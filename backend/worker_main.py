"""Standalone supervised Twilio outbox worker entry point."""
from __future__ import annotations

import os
from bridge_core.config import bounded_float_from_env, database_url_from_env
import socket
import psycopg
from twilio.rest import Client

from bridge_core.address_vault import EncryptedParticipantAddressCodec, PostgresParticipantAddressResolver
from bridge_core.dispatcher import OutboxCommandDispatcher
from bridge_core.persistence import PostgresBridgeRepository
from bridge_core.worker import SupervisedOutboxWorker
from providers.twilio.adapter import TwilioConferenceCommandAdapter
from providers.twilio.resource_resolver import PostgresTwilioResourceResolver


def main():
    try:
        dsn = database_url_from_env()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None
    def connect():
        return psycopg.connect(dsn)
    def required(name):
        value = os.environ.get(name, "").strip()
        if not value:
            raise SystemExit(f"{name} is required")
        return value

    account_sid = required("TWILIO_ACCOUNT_SID")
    auth_token = required("TWILIO_AUTH_TOKEN")
    provider_account_id = required("TWILIO_PROVIDER_ACCOUNT_ID")
    api_username = os.environ.get("TWILIO_API_KEY", "").strip() or account_sid
    api_password = os.environ.get("TWILIO_API_SECRET", "").strip() or auth_token
    request_timeout_seconds = bounded_float_from_env(
        "TWILIO_REQUEST_TIMEOUT_SECONDS", 10.0, minimum=1.0, maximum=12.0,
    )
    client = Client(
        api_username, api_password, account_sid=account_sid,
        http_timeout=request_timeout_seconds,
    )
    codec = EncryptedParticipantAddressCodec(bytes.fromhex(required("PARTICIPANT_ADDRESS_KEY_HEX")))
    vault = PostgresParticipantAddressResolver(connect=connect, codec=codec)
    resolver = PostgresTwilioResourceResolver(connect=connect, provider_account_id=provider_account_id)
    adapter = TwilioConferenceCommandAdapter(
        client=client, account_sid=account_sid,
        from_number=required("TWILIO_FROM_NUMBER"),
        public_origin=required("TWILIO_PUBLIC_ORIGIN"),
        consent_disclosure=required("TWILIO_CONSENT_DISCLOSURE"),
        address_resolver=lambda session_id, ref: vault.resolve(
            tenant_id=resolver.tenant_for_session(session_id), participant_ref=ref,
        ),
        session_guard=resolver.ensure_consent_open,
    )
    dispatcher = OutboxCommandDispatcher(
        repository=PostgresBridgeRepository(connect),
        adapters={("twilio", provider_account_id): adapter},
        worker_id=os.environ.get("WORKER_ID", socket.gethostname()),
        lease_seconds=60, retry_delay_seconds=5,
    )
    worker = SupervisedOutboxWorker(
        dispatcher=dispatcher, worker_id=os.environ.get("WORKER_ID", socket.gethostname()),
        poll_interval_seconds=float(os.environ.get("WORKER_POLL_SECONDS", "1")),
        batch_size=int(os.environ.get("WORKER_BATCH_SIZE", "1")),
    )
    try:
        worker.run_forever()
    except KeyboardInterrupt:
        worker.stop()


if __name__ == "__main__":
    main()
