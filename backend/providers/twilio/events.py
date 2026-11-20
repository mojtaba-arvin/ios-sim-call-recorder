"""Strict Twilio form-event normalization after signature verification.

The decoder deliberately accepts only explicitly configured callback routes and
never persists phone numbers, raw Twilio SIDs, or recording URLs in domain events.
"""
from __future__ import annotations

import hashlib
import hmac
import re
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import TypeAlias
from urllib.parse import urlsplit

from bridge_core.domain import EventType
from bridge_core.ports import SignedWebhookRequest
from bridge_core.webhooks import NormalizedProviderEvent

SessionResolver: TypeAlias = Callable[
    [str | None, str | None], tuple[str, str | None]
]
_ACCOUNT_SID = re.compile(r"^AC[0-9a-fA-F]{32}$")


class TwilioEventDecodeError(ValueError):
    """A signed request is not a supported, well-formed Twilio callback."""


class TwilioWebhookEventDecoder:
    """Decode consent, Conference and Recording callbacks for one Twilio account.

    `resolve_session` must resolve the supplied opaque Twilio resource IDs against
    this provider account's immutable database mappings and return an internal
    session ID plus an optional opaque participant reference. It must never infer
    ownership from a caller-supplied session ID.
    """

    def __init__(
        self,
        *,
        account_sid: str,
        provider_account_id: str,
        consent_policy_version: str,
        resolve_session: SessionResolver,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not _ACCOUNT_SID.fullmatch(account_sid):
            raise ValueError("a valid Twilio Account SID is required")
        for name, value in (
            ("provider_account_id", provider_account_id),
            ("consent_policy_version", consent_policy_version),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        self._account_sid = account_sid
        self._provider_account_id = provider_account_id
        self._consent_policy_version = consent_policy_version
        self._resolve_session = resolve_session
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __call__(self, request: SignedWebhookRequest) -> NormalizedProviderEvent:
        if request.method.upper() != "POST":
            raise TwilioEventDecodeError("Twilio callbacks must use POST")
        media_type = request.content_type.split(";", 1)[0].strip().lower()
        if media_type != "application/x-www-form-urlencoded":
            raise TwilioEventDecodeError("Twilio callback must be form encoded")
        if request.form_parameters is None:
            raise TwilioEventDecodeError("Twilio callback form fields are missing")

        fields = self._single_value_fields(request.form_parameters)
        supplied_account = fields.get("AccountSid", "")
        if not hmac.compare_digest(supplied_account, self._account_sid):
            raise TwilioEventDecodeError("Twilio account does not match configured account")

        route = urlsplit(request.public_url).path.rstrip("/").rsplit("/", 1)[-1]
        call_sid = fields.get("CallSid") or None
        conference_sid = fields.get("ConferenceSid") or None
        if not call_sid and not conference_sid:
            raise TwilioEventDecodeError("Twilio resource identity is missing")

        try:
            session_id, participant_ref = self._resolve_session(call_sid, conference_sid)
        except Exception as exc:
            # Resolver exceptions may contain provider IDs; do not propagate them.
            raise TwilioEventDecodeError("Twilio resource is not owned by this account") from None
        if not isinstance(session_id, str) or not session_id.strip():
            raise TwilioEventDecodeError("resolved session identity is invalid")
        if participant_ref is not None and (
            not isinstance(participant_ref, str)
            or not participant_ref.strip()
            or participant_ref != participant_ref.strip()
            or any(char.isspace() for char in participant_ref)
            or len(participant_ref) > 128
        ):
            raise TwilioEventDecodeError("resolved participant reference is invalid")

        event_type: EventType
        consent_method = None
        policy_version = None
        if route == "consent":
            if fields.get("Digits") != "1":
                raise TwilioEventDecodeError("affirmative consent digit was not received")
            if participant_ref is None:
                raise TwilioEventDecodeError("consent callback has no mapped participant")
            event_type = EventType.PARTICIPANT_CONSENTED
            consent_method = "dtmf_1"
            policy_version = self._consent_policy_version
        elif route == "conference":
            callback_event = fields.get("StatusCallbackEvent", "")
            if callback_event == "conference-start":
                event_type = EventType.BRIDGE_RINGING
            elif callback_event == "participant-join":
                if participant_ref is None:
                    raise TwilioEventDecodeError("participant callback has no mapped participant")
                event_type = EventType.PARTICIPANT_JOINED
            elif callback_event == "conference-end":
                event_type = EventType.CALL_ENDED
            else:
                raise TwilioEventDecodeError("unsupported Twilio Conference callback")
        elif route == "recording":
            status = fields.get("RecordingStatus", "")
            if status == "completed":
                event_type = EventType.RECORDING_READY
            elif status == "failed":
                event_type = EventType.RECORDING_FAILED
            else:
                raise TwilioEventDecodeError("unsupported Twilio Recording callback")
        else:
            raise TwilioEventDecodeError("unknown Twilio callback route")

        occurred_at = self._parse_timestamp(fields.get("Timestamp")) or self._clock()
        if occurred_at.tzinfo is None:
            raise TwilioEventDecodeError("event clock must return a timezone-aware timestamp")
        payload_digest = hashlib.sha256(request.raw_body).hexdigest()
        idempotency_token = request.headers.get("i-twilio-idempotency-token", "").strip()
        if idempotency_token:
            identity_material = f"{self._account_sid}\0{idempotency_token}".encode()
        else:
            # Stable fallback for Twilio callbacks without an idempotency header.
            # Only the digest is persisted; raw fields and provider SIDs are not.
            identity_material = b"\0".join((
                self._account_sid.encode(),
                route.encode(),
                (call_sid or "").encode(),
                (conference_sid or "").encode(),
                payload_digest.encode(),
            ))
        event_id = "twilio_" + hashlib.sha256(identity_material).hexdigest()
        return NormalizedProviderEvent(
            provider="twilio",
            provider_account_id=self._provider_account_id,
            event_id=event_id,
            session_id=session_id,
            event_type=event_type,
            occurred_at=occurred_at,
            participant_ref=participant_ref if event_type in {
                EventType.PARTICIPANT_JOINED, EventType.PARTICIPANT_CONSENTED
            } else None,
            payload_digest=payload_digest,
            consent_policy_version=policy_version,
            consent_method=consent_method,
        )

    @staticmethod
    def _single_value_fields(
        parameters: Mapping[str, str | Sequence[str]],
    ) -> dict[str, str]:
        fields: dict[str, str] = {}
        for key, raw in parameters.items():
            if not isinstance(key, str) or not key:
                raise TwilioEventDecodeError("invalid Twilio form field")
            if isinstance(raw, str):
                value = raw
            elif isinstance(raw, Sequence) and not isinstance(raw, (bytes, bytearray)):
                if len(raw) != 1:
                    raise TwilioEventDecodeError("duplicate Twilio form field")
                value = raw[0]
            else:
                raise TwilioEventDecodeError("invalid Twilio form field value")
            if not isinstance(value, str):
                raise TwilioEventDecodeError("invalid Twilio form field value")
            fields[key] = value
        return fields

    @staticmethod
    def _parse_timestamp(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if parsed is None or parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
