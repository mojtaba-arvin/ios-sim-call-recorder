"""Raw-body verification and deterministic provider-event reduction."""
from __future__ import annotations
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from .application import EventApplication, OutboxCommand
from .domain import BridgeSession, EventType, InvalidTransition, SessionState
from .ports import BridgeRepository, SignedWebhookRequest, WebhookSignatureVerifier

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
    provider_account_id: str = "default"

    def __post_init__(self):
        for name in ("provider", "provider_account_id", "event_id", "session_id"):
            if not getattr(self, name).strip(): raise ValueError(f"{name} must not be empty")
        if self.occurred_at.tzinfo is None: raise ValueError("occurred_at must be timezone-aware")
        if self.event_type in {EventType.PARTICIPANT_JOINED, EventType.PARTICIPANT_CONSENTED}:
            if not self.participant_ref or not self.participant_ref.strip():
                raise ValueError("participant event requires opaque participant_ref")

class WebhookProcessor:
    """Verifies bytes BEFORE decoding, then delegates an atomic event application."""
    def __init__(self, *, verifier: WebhookSignatureVerifier, repository: BridgeRepository):
        self._verifier, self._repository = verifier, repository

    def process(self, *, request: SignedWebhookRequest,
                decode: Callable[[SignedWebhookRequest], NormalizedProviderEvent]) -> bool:
        # Provider-native verification runs before business payload decoding.
        if not self._verifier.verify(request):
            raise InvalidWebhookSignature("provider webhook signature verification failed")
        # Pass the exact verified request object so form validators and event
        # decoders consume the same parsed parameters, avoiding parser drift.
        event = decode(request)
        def apply(session: BridgeSession) -> EventApplication:
            if session.session_id != event.session_id: raise UnknownSession(event.session_id)
            return self._reduce(session, event)
        try:
            return self._repository.apply_event_once(
                event.provider, event.event_id, event.session_id, apply,
                provider_account_id=event.provider_account_id,
                payload_digest=event.payload_digest,
            )
        except KeyError as exc:
            raise UnknownSession(event.session_id) from exc

    @staticmethod
    def _reduce(session: BridgeSession, event: NormalizedProviderEvent) -> EventApplication:
        at, kind = event.occurred_at, event.event_type
        if session.updated_at is not None and at < session.updated_at:
            raise InvalidTransition("stale provider event cannot move session state backwards")
        if kind is EventType.BRIDGE_RINGING:
            return EventApplication(session.transition(SessionState.BRIDGE_LEG_RINGING, at=at))
        if kind is EventType.PARTICIPANT_JOINED:
            return EventApplication(session.participant_joined(event.participant_ref, at=at))
        if kind is EventType.PARTICIPANT_CONSENTED:
            updated = session.participant_consented(event.participant_ref, at=at)
            commands = ()
            if updated.all_participants_consented and not session.all_participants_consented:
                commands = (OutboxCommand(
                    command_type="recording.start",
                    idempotency_key=f"recording-start:{event.provider}:{event.provider_account_id}:{event.session_id}",
                    session_id=event.session_id, provider=event.provider,
                    provider_account_id=event.provider_account_id,
                    payload={"session_id": event.session_id},
                ),)
            return EventApplication(updated, commands)
        if kind is EventType.RECORDING_STARTED:
            return EventApplication(session.transition(SessionState.RECORDING, at=at))
        if kind is EventType.CALL_ENDED:
            if session.state is SessionState.RECORDING:
                return EventApplication(session.transition(SessionState.FINALIZING, at=at))
            return EventApplication(session.transition(SessionState.FAILED, failure_code="call_ended_before_recording", at=at))
        if kind is EventType.RECORDING_READY:
            return EventApplication(session.transition(SessionState.VERIFYING, at=at))
        if kind is EventType.RECORDING_FAILED:
            return EventApplication(session.transition(SessionState.FAILED, failure_code="provider_recording_failed", at=at))
        raise InvalidTransition(f"unsupported provider event: {kind}")
