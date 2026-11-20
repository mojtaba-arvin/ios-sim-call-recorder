"""Live Twilio Programmable Voice adapter for consent and Conference commands.

All provider calls happen outside database transactions. Uncertain retries fail
closed: Twilio Calls/Conference resources are reconciled before a new side effect.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

from bridge_core.dispatcher import (
    ProviderExecutionResult,
    ProviderOperationError,
    ReconciliationResult,
    ReconciliationState,
)
from bridge_core.persistence import LeasedCommand
from .consent import build_consent_gather_twiml

_SID = {
    "AC": re.compile(r"^AC[0-9a-fA-F]{32}$"),
    "CA": re.compile(r"^CA[0-9a-fA-F]{32}$"),
    "CF": re.compile(r"^CF[0-9a-fA-F]{32}$"),
}


class TwilioConferenceCommandAdapter:
    """Twilio REST adapter; addresses are resolved only at the last responsible moment."""

    def __init__(
        self,
        *,
        client: Any,
        account_sid: str,
        from_number: str,
        public_origin: str,
        consent_disclosure: str,
        address_resolver: Callable[[str, str], str],
        request_timeout_seconds: float = 10.0,
    ) -> None:
        if not _SID["AC"].fullmatch(account_sid):
            raise ValueError("valid Twilio Account SID is required")
        if not from_number.startswith("+") or not re.fullmatch(r"\+[1-9][0-9]{7,14}", from_number):
            raise ValueError("Twilio caller ID must be an E.164 number")
        if not public_origin.startswith("https://") or public_origin.endswith("/"):
            raise ValueError("public_origin must be an HTTPS origin without trailing slash")
        if not consent_disclosure.strip() or len(consent_disclosure) > 4000:
            raise ValueError("a reviewed consent disclosure is required")
        if not 1 <= request_timeout_seconds <= 12:
            raise ValueError("Twilio request timeout must be between 1 and 12 seconds")
        self.client = client
        self.account_sid = account_sid
        self.from_number = from_number
        self.public_origin = public_origin
        self.consent_disclosure = consent_disclosure
        self.address_resolver = address_resolver
        self.request_timeout_seconds = request_timeout_seconds

    @staticmethod
    def conference_name(session_id: str) -> str:
        digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:40]
        return "bridge-" + digest

    def _address(self, command: LeasedCommand) -> str:
        ref = command.payload.get("participant_ref")
        if not isinstance(ref, str) or not ref or ref != ref.strip():
            raise ProviderOperationError("participant_reference_invalid", retryable=False)
        try:
            address = self.address_resolver(command.session_id, ref)
        except Exception:
            raise ProviderOperationError("participant_address_unavailable", retryable=False) from None
        if not isinstance(address, str) or not re.fullmatch(r"\+[1-9][0-9]{7,14}", address):
            raise ProviderOperationError("participant_address_invalid", retryable=False)
        return address

    def _conference_callbacks(self) -> dict[str, Any]:
        return {
            "conference_status_callback": self.public_origin + "/v1/twilio/conference",
            "conference_status_callback_method": "POST",
            "conference_status_callback_event": ["start", "end", "join", "leave"],
            "recording_status_callback": self.public_origin + "/v1/twilio/recording",
            "recording_status_callback_method": "POST",
            "recording_status_callback_event": ["completed", "failed", "absent"],
            "recording_channels": "dual",
            "beep": "false",
            "start_conference_on_enter": True,
        }

    def _fetch_participants(self, conference_sid: str) -> list[Any]:
        return self.client.conferences(conference_sid).participants.list(limit=250)

    @staticmethod
    def _matching_participant(participants: list[Any], participant_ref: str) -> Any | None:
        matches = [item for item in participants if getattr(item, "label", None) == participant_ref]
        if len(matches) > 1:
            raise ProviderOperationError("provider_participant_mapping_ambiguous", retryable=False)
        return matches[0] if matches else None

    def reconcile(
        self,
        command: LeasedCommand,
        *,
        conference_sid: str | None,
        call_sid: str | None,
    ) -> ReconciliationResult:
        kind = command.command_type
        ref = command.payload.get("participant_ref")
        try:
            if kind == "consent.request":
                if call_sid:
                    call = self.client.calls(call_sid).fetch()
                    return ReconciliationResult(ReconciliationState.APPLIED, call_sid=call.sid)
                # Calls.create has no general idempotency-key contract. After an
                # uncertain first attempt, never dial the same person a second time.
                return ReconciliationResult(
                    ReconciliationState.NOT_APPLIED if command.attempts == 1 else ReconciliationState.UNKNOWN
                )

            if kind in {"conference.create", "participant.add"}:
                if conference_sid:
                    conference = self.client.conferences(conference_sid).fetch()
                    if getattr(conference, "status", None) == "completed":
                        return ReconciliationResult(ReconciliationState.UNKNOWN)
                    participant = self._matching_participant(
                        self._fetch_participants(conference_sid), str(ref)
                    )
                    if participant is not None:
                        return ReconciliationResult(
                            ReconciliationState.APPLIED,
                            conference_sid=conference_sid,
                            call_sid=participant.call_sid,
                        )
                    return ReconciliationResult(ReconciliationState.UNKNOWN)

                name = self.conference_name(command.session_id)
                conferences = self.client.conferences.list(
                    friendly_name=name, status="in-progress", limit=10
                )
                if len(conferences) > 1:
                    return ReconciliationResult(ReconciliationState.UNKNOWN)
                if conferences:
                    found = conferences[0]
                    participant = self._matching_participant(
                        self._fetch_participants(found.sid), str(ref)
                    )
                    if participant is not None:
                        return ReconciliationResult(
                            ReconciliationState.APPLIED,
                            conference_sid=found.sid,
                            call_sid=participant.call_sid,
                        )
                    return ReconciliationResult(ReconciliationState.UNKNOWN)
                return ReconciliationResult(
                    ReconciliationState.NOT_APPLIED if command.attempts == 1 else ReconciliationState.UNKNOWN
                )

            if kind == "conference.close":
                if not conference_sid:
                    return ReconciliationResult(ReconciliationState.NOT_APPLIED)
                conference = self.client.conferences(conference_sid).fetch()
                if getattr(conference, "status", None) == "completed":
                    return ReconciliationResult(ReconciliationState.APPLIED, conference_sid=conference_sid)
                return ReconciliationResult(ReconciliationState.NOT_APPLIED, conference_sid=conference_sid)

            raise ProviderOperationError("provider_command_unsupported", retryable=False)
        except ProviderOperationError:
            raise
        except Exception as exc:
            status = getattr(exc, "status", None)
            if status == 404 and command.attempts == 1:
                return ReconciliationResult(ReconciliationState.NOT_APPLIED)
            if status == 404:
                return ReconciliationResult(ReconciliationState.UNKNOWN)
            raise self._provider_error(exc) from None

    def execute(
        self,
        command: LeasedCommand,
        *,
        conference_sid: str | None,
        call_sid: str | None,
    ) -> ProviderExecutionResult:
        try:
            kind = command.command_type
            if kind == "consent.request":
                address = self._address(command)
                action = self.public_origin + "/v1/twilio/consent"
                twiml = build_consent_gather_twiml(
                    disclosure=self.consent_disclosure, action_url=action
                )
                call = self.client.calls.create(
                    to=address,
                    from_=self.from_number,
                    twiml=twiml,
                    timeout=30,
                )
                return ProviderExecutionResult(call_sid=call.sid)

            if kind in {"conference.create", "participant.add"}:
                if kind == "conference.create" and command.payload.get("recording_mode") != "from_start":
                    raise ProviderOperationError("conference_recording_mode_invalid", retryable=False)
                address = self._address(command)
                name_or_sid = (
                    self.conference_name(command.session_id)
                    if kind == "conference.create"
                    else conference_sid
                )
                if not name_or_sid:
                    raise ProviderOperationError("provider_conference_sid_missing", retryable=True)
                participant = self.client.conferences(name_or_sid).participants.create(
                    to=address,
                    from_=self.from_number,
                    label=str(command.payload["participant_ref"]),
                    conference_record="record-from-start" if kind == "conference.create" else "true",
                    **self._conference_callbacks(),
                )
                returned_conference = getattr(participant, "conference_sid", None) or conference_sid
                if returned_conference and not _SID["CF"].fullmatch(returned_conference):
                    raise ProviderOperationError("provider_conference_sid_invalid", retryable=True)
                if not _SID["CA"].fullmatch(participant.call_sid):
                    raise ProviderOperationError("provider_call_sid_invalid", retryable=True)
                return ProviderExecutionResult(
                    conference_sid=returned_conference,
                    call_sid=participant.call_sid,
                )

            if kind == "conference.close":
                if not conference_sid:
                    return ProviderExecutionResult()
                self.client.conferences(conference_sid).update(status="completed")
                return ProviderExecutionResult(conference_sid=conference_sid)

            raise ProviderOperationError("provider_command_unsupported", retryable=False)
        except ProviderOperationError:
            raise
        except Exception as exc:
            raise self._provider_error(exc) from None

    @staticmethod
    def _provider_error(exc: Exception) -> ProviderOperationError:
        status = getattr(exc, "status", None)
        code = getattr(exc, "code", None)
        if status == 429 or (isinstance(status, int) and status >= 500):
            return ProviderOperationError("twilio_temporarily_unavailable", retryable=True)
        if isinstance(status, int) and 400 <= status < 500:
            return ProviderOperationError("twilio_request_rejected", retryable=False)
        return ProviderOperationError("twilio_transport_error", retryable=True)
