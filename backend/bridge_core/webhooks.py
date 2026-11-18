"""Raw-body verification and deterministic provider-event reduction."""
from __future__ import annotations
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from .domain import BridgeSession, EventType, InvalidTransition, SessionState
from .ports import BridgeRepository, WebhookSignatureVerifier

class InvalidWebhookSignature(PermissionError): pass
class UnknownSession(LookupError): pass

@dataclass(frozen=True, slots=True)
class NormalizedProviderEvent:
    provider: str
    event_id: str
    session_id: str
    event_type: EventType
    occurred_at: datetime
    participant_ref: str | None = None
    payload_digest: str = ""

    def __post_init__(self):
        for name in ("provider", "event_id", "session_id"):
            if not getattr(self, name).strip(): raise ValueError(f"{name} must not be empty")
        if self.occurred_at.tzinfo is None: raise ValueError("occurred_at must be timezone-aware")
        if self.event_type in {EventType.PARTICIPANT_JOINED, EventType.PARTICIPANT_CONSENTED}:
            if not self.participant_ref or not self.participant_ref.strip():
                raise ValueError("participant event requires opaque participant_ref")

class WebhookProcessor:
    """Verifies bytes BEFORE decoding, then delegates an atomic event application."""
    def __init__(self, *, verifier: WebhookSignatureVerifier, repository: BridgeRepository):
        self._verifier, self._repository = verifier, repository

    def process(self, *, raw_body: bytes, headers: Mapping[str, str],
                decode: Callable[[bytes], NormalizedProviderEvent]) -> bool:
        if not self._verifier.verify(raw_body, headers):
            raise InvalidWebhookSignature("provider webhook signature verification failed")
        event = decode(raw_body)
        def apply(session: BridgeSession) -> BridgeSession:
            if session.session_id != event.session_id: raise UnknownSession(event.session_id)
            return self._reduce(session, event)
        try:
            return self._repository.apply_event_once(event.provider, event.event_id, event.session_id, apply)
        except KeyError as exc:
            raise UnknownSession(event.session_id) from exc

    @staticmethod
    def _reduce(session: BridgeSession, event: NormalizedProviderEvent) -> BridgeSession:
        at, kind = event.occurred_at, event.event_type
        if kind is EventType.BRIDGE_RINGING:
            return session.transition(SessionState.BRIDGE_LEG_RINGING, at=at)
        if kind is EventType.PARTICIPANT_JOINED:
            return session.participant_joined(event.participant_ref, at=at)
        if kind is EventType.PARTICIPANT_CONSENTED:
            return session.participant_consented(event.participant_ref, at=at)
        if kind is EventType.RECORDING_STARTED:
            return session.transition(SessionState.RECORDING, at=at)
        if kind is EventType.CALL_ENDED:
            if session.state is SessionState.RECORDING:
                return session.transition(SessionState.FINALIZING, at=at)
            return session.transition(SessionState.FAILED, failure_code="call_ended_before_recording", at=at)
        if kind is EventType.RECORDING_READY:
            return session.transition(SessionState.VERIFYING, at=at)
        if kind is EventType.RECORDING_FAILED:
            return session.transition(SessionState.FAILED, failure_code="provider_recording_failed", at=at)
        raise InvalidTransition(f"unsupported provider event: {kind}")
