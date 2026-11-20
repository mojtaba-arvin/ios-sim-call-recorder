"""Production ASGI composition root. Twilio is opt-in and fails closed when enabled."""
from __future__ import annotations

import json
import os
from bridge_core.config import database_url_from_env

import boto3
import psycopg
from twilio.rest import Client

from bridge_core.address_vault import EncryptedParticipantAddressCodec, PostgresParticipantAddressResolver
from bridge_core.http_api import BearerTokenAuthenticator, BridgeSessionsASGI
from bridge_core.object_storage import S3MediaObjectStore
from bridge_core.persistence import PostgresBridgeRepository
from bridge_core.webhooks import WebhookProcessor
from providers.twilio.adapter import TwilioConferenceCommandAdapter
from providers.twilio.events import TwilioWebhookEventDecoder
from providers.twilio.factory import TwilioConsentCommandFactory
from providers.twilio.ingress import TwilioWebhookASGI
from providers.twilio.media import TwilioRecordingMediaIngestor
from providers.twilio.resource_resolver import PostgresTwilioResourceResolver
from providers.twilio.signatures import TwilioWebhookSignatureVerifier


class ApplicationRouter:
    def __init__(self, *, sessions, webhooks=None):
        self.sessions, self.webhooks = sessions, webhooks

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        if path.startswith("/v1/twilio/"):
            if self.webhooks is None:
                await BridgeSessionsASGI.respond(send, 404, {"error": "not_found"})
            else:
                await self.webhooks(scope, receive, send)
            return
        await self.sessions(scope, receive, send)


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} must be injected by the deployment secret manager")
    return value


def _twilio_runtime(connect):
    account_sid = _required("TWILIO_ACCOUNT_SID")
    auth_token = _required("TWILIO_AUTH_TOKEN")
    provider_account_id = _required("TWILIO_PROVIDER_ACCOUNT_ID")
    from_number = _required("TWILIO_FROM_NUMBER")
    public_origin = _required("TWILIO_PUBLIC_ORIGIN")
    policy_version = _required("TWILIO_CONSENT_POLICY_VERSION")
    disclosure = _required("TWILIO_CONSENT_DISCLOSURE")
    key = bytes.fromhex(_required("PARTICIPANT_ADDRESS_KEY_HEX"))
    api_username = os.environ.get("TWILIO_API_KEY", "").strip() or account_sid
    api_password = os.environ.get("TWILIO_API_SECRET", "").strip() or auth_token
    client = Client(api_username, api_password, account_sid=account_sid, http_timeout=10)
    codec = EncryptedParticipantAddressCodec(key)
    vault = PostgresParticipantAddressResolver(connect=connect, codec=codec)
    resolver = PostgresTwilioResourceResolver(connect=connect, provider_account_id=provider_account_id)
    adapter = TwilioConferenceCommandAdapter(
        client=client, account_sid=account_sid, from_number=from_number,
        public_origin=public_origin, consent_disclosure=disclosure,
        address_resolver=lambda session_id, ref: vault.resolve(
            tenant_id=resolver.tenant_for_session(session_id), participant_ref=ref,
        ),
        session_guard=resolver.ensure_consent_open,
    )
    decoder = TwilioWebhookEventDecoder(
        account_sid=account_sid, provider_account_id=provider_account_id,
        consent_policy_version=policy_version, resolve_session=resolver,
    )
    processor = WebhookProcessor(
        verifier=TwilioWebhookSignatureVerifier(auth_token), repository=PostgresBridgeRepository(connect),
    )
    bucket = _required("MEDIA_BUCKET")
    kms_key = _required("MEDIA_KMS_KEY_ID")
    s3 = boto3.client("s3")
    object_store = S3MediaObjectStore(client=s3, bucket=bucket, kms_key_id=kms_key)
    media_ingestor = TwilioRecordingMediaIngestor(
        account_sid=account_sid, api_username=api_username, api_password=api_password,
        provider_account_id=provider_account_id, connect=connect,
        resource_resolver=resolver, object_store=object_store,
        retention_days=int(os.environ.get("MEDIA_RETENTION_DAYS", "30")),
    )
    return client, adapter, decoder, processor, media_ingestor, provider_account_id, vault


def create_app():
    database_url = database_url_from_env()
    token_json = os.environ.get("BRIDGE_API_TOKEN_HASHES", "")
    if not token_json:
        raise RuntimeError("BRIDGE_API_TOKEN_HASHES must be injected by the deployment secret manager")
    try:
        token_hashes = json.loads(token_json)
    except json.JSONDecodeError as exc:
        raise RuntimeError("BRIDGE_API_TOKEN_HASHES must be valid JSON") from exc
    if not isinstance(token_hashes, dict):
        raise RuntimeError("BRIDGE_API_TOKEN_HASHES must be an object")
    connect = lambda: psycopg.connect(database_url)
    repository = PostgresBridgeRepository(connect)
    authenticator = BearerTokenAuthenticator(token_hashes)

    if os.environ.get("TWILIO_ENABLED", "false").lower() != "true":
        return ApplicationRouter(sessions=BridgeSessionsASGI(
            repository=repository, authenticator=authenticator,
        ))

    client, adapter, decoder, processor, media_ingestor, provider_account_id, vault = _twilio_runtime(connect)
    sessions = BridgeSessionsASGI(
        repository=repository,
        authenticator=authenticator,
        initial_commands=TwilioConsentCommandFactory(provider_account_id=provider_account_id),
        address_vault=vault,
    )
    webhooks = TwilioWebhookASGI(
        processor=processor,
        decode_verified_request=decoder,
        canonical_public_origin=_required("TWILIO_PUBLIC_ORIGIN"),
        after_process=media_ingestor,
    )
    return ApplicationRouter(sessions=sessions, webhooks=webhooks)
