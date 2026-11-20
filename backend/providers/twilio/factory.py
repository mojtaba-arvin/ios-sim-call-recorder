"""Transactional initial consent command creation for Twilio sessions."""
from __future__ import annotations

from bridge_core.application import OutboxCommand
from bridge_core.domain import BridgeSession


class TwilioConsentCommandFactory:
    def __init__(self, *, provider_account_id: str):
        if not provider_account_id or not provider_account_id.strip():
            raise ValueError("provider account identifier is required")
        self.provider_account_id = provider_account_id

    def __call__(self, session: BridgeSession) -> tuple[OutboxCommand, ...]:
        return tuple(
            OutboxCommand(
                command_type="consent.request",
                idempotency_key=f"consent-request:twilio:{self.provider_account_id}:{session.session_id}:{participant_ref}",
                session_id=session.session_id,
                provider="twilio",
                provider_account_id=self.provider_account_id,
                payload={"participant_ref": participant_ref},
            )
            for participant_ref in sorted(session.expected_participant_refs)
        )
