"""Provider-neutral conference bridge session domain."""
from __future__ import annotations
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum

class SessionState(StrEnum):
    CREATED = "created"
    AWAITING_USER_ACTION = "awaiting_user_action"
    BRIDGE_LEG_RINGING = "bridge_leg_ringing"
    PARTICIPANTS_JOINING = "participants_joining"
    AWAITING_CONSENT = "awaiting_consent"
    RECORDING = "recording"
    FINALIZING = "finalizing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    DEGRADED = "degraded"
    FAILED = "failed"
    CANCELLED = "cancelled"

class EventType(StrEnum):
    BRIDGE_RINGING = "bridge.ringing"
    PARTICIPANT_JOINED = "participant.joined"
    PARTICIPANT_CONSENTED = "participant.consent_granted"
    RECORDING_STARTED = "recording.started"
    CALL_ENDED = "call.ended"
    RECORDING_READY = "recording.ready"
    RECORDING_FAILED = "recording.failed"

class InvalidTransition(ValueError): pass
class ConsentRequired(PermissionError): pass
class InvalidParticipant(ValueError): pass

_ALLOWED = {
    SessionState.CREATED: {SessionState.AWAITING_USER_ACTION, SessionState.CANCELLED, SessionState.FAILED},
    SessionState.AWAITING_USER_ACTION: {SessionState.BRIDGE_LEG_RINGING, SessionState.PARTICIPANTS_JOINING, SessionState.CANCELLED, SessionState.FAILED},
    SessionState.BRIDGE_LEG_RINGING: {SessionState.PARTICIPANTS_JOINING, SessionState.AWAITING_CONSENT, SessionState.CANCELLED, SessionState.FAILED},
    SessionState.PARTICIPANTS_JOINING: {SessionState.AWAITING_CONSENT, SessionState.CANCELLED, SessionState.FAILED},
    SessionState.AWAITING_CONSENT: {SessionState.RECORDING, SessionState.CANCELLED, SessionState.FAILED},
    SessionState.RECORDING: {SessionState.FINALIZING, SessionState.CANCELLED, SessionState.FAILED},
    SessionState.FINALIZING: {SessionState.VERIFYING, SessionState.DEGRADED, SessionState.FAILED},
    SessionState.VERIFYING: {SessionState.COMPLETED, SessionState.DEGRADED, SessionState.FAILED},
    SessionState.COMPLETED: set(), SessionState.DEGRADED: set(),
    SessionState.FAILED: set(), SessionState.CANCELLED: set(),
}

@dataclass(frozen=True, slots=True)
class BridgeSession:
    session_id: str
    expected_participants: int
    state: SessionState = SessionState.CREATED
    joined_participants: frozenset[str] = field(default_factory=frozenset)
    consented_participants: frozenset[str] = field(default_factory=frozenset)
    failure_code: str | None = None
    updated_at: datetime | None = None

    def __post_init__(self):
        if not self.session_id.strip(): raise ValueError("session_id must not be empty")
        if self.expected_participants < 2: raise ValueError("a bridge requires at least two participants")
        if len(self.joined_participants) > self.expected_participants: raise ValueError("too many joined participants")
        if not self.consented_participants.issubset(self.joined_participants):
            raise ValueError("consent can only be recorded for joined participants")

    @property
    def all_participants_joined(self) -> bool:
        return len(self.joined_participants) == self.expected_participants

    @property
    def all_participants_consented(self) -> bool:
        return self.all_participants_joined and self.consented_participants == self.joined_participants

    def transition(self, target: SessionState, *, failure_code: str | None = None,
                   at: datetime | None = None) -> BridgeSession:
        if target not in _ALLOWED[self.state]:
            raise InvalidTransition(f"{self.state.value} -> {target.value} is not allowed")
        if target is SessionState.RECORDING and not self.all_participants_consented:
            raise ConsentRequired("every expected participant must affirmatively consent")
        if target is SessionState.FAILED and not failure_code:
            raise ValueError("failed sessions require a stable failure code")
        return replace(self, state=target, failure_code=failure_code, updated_at=at)

    def participant_joined(self, participant_ref: str, *, at: datetime | None = None) -> BridgeSession:
        self._require_ref(participant_ref)
        if self.state not in {SessionState.BRIDGE_LEG_RINGING, SessionState.PARTICIPANTS_JOINING}:
            raise InvalidTransition(f"participants cannot join while {self.state.value}")
        if participant_ref in self.joined_participants: return self
        if len(self.joined_participants) >= self.expected_participants:
            raise InvalidParticipant("more participants joined than expected")
        updated = replace(self, joined_participants=self.joined_participants | {participant_ref}, updated_at=at)
        if updated.all_participants_joined:
            return updated.transition(SessionState.AWAITING_CONSENT, at=at)
        if self.state is SessionState.BRIDGE_LEG_RINGING:
            return updated.transition(SessionState.PARTICIPANTS_JOINING, at=at)
        return updated

    def participant_consented(self, participant_ref: str, *, at: datetime | None = None) -> BridgeSession:
        self._require_ref(participant_ref)
        if self.state is not SessionState.AWAITING_CONSENT:
            raise InvalidTransition("consent is accepted only after all participants join")
        if participant_ref not in self.joined_participants:
            raise InvalidParticipant("consenting participant has not joined")
        return replace(self, consented_participants=self.consented_participants | {participant_ref}, updated_at=at)

    @staticmethod
    def _require_ref(value: str) -> None:
        if not value or not value.strip(): raise InvalidParticipant("opaque participant reference is required")
