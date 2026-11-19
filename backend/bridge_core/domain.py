"""Provider-neutral conference bridge session domain."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum


class SessionState(StrEnum):
    CREATED = "created"
    AWAITING_USER_ACTION = "awaiting_user_action"
    BRIDGE_LEG_RINGING = "bridge_leg_ringing"
    AWAITING_CONSENT = "awaiting_consent"
    PARTICIPANTS_JOINING = "participants_joining"
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


class InvalidTransition(ValueError):
    pass


class ConsentRequired(PermissionError):
    pass


class InvalidParticipant(ValueError):
    pass


_ALLOWED = {
    SessionState.CREATED: {
        SessionState.AWAITING_USER_ACTION, SessionState.CANCELLED, SessionState.FAILED,
    },
    SessionState.AWAITING_USER_ACTION: {
        SessionState.BRIDGE_LEG_RINGING, SessionState.AWAITING_CONSENT,
        SessionState.CANCELLED, SessionState.FAILED,
    },
    SessionState.BRIDGE_LEG_RINGING: {
        SessionState.AWAITING_CONSENT, SessionState.PARTICIPANTS_JOINING,
        SessionState.CANCELLED, SessionState.FAILED,
    },
    SessionState.AWAITING_CONSENT: {
        SessionState.PARTICIPANTS_JOINING, SessionState.CANCELLED, SessionState.FAILED,
    },
    SessionState.PARTICIPANTS_JOINING: {
        SessionState.RECORDING, SessionState.CANCELLED, SessionState.FAILED,
    },
    SessionState.RECORDING: {
        SessionState.FINALIZING, SessionState.CANCELLED, SessionState.FAILED,
    },
    SessionState.FINALIZING: {
        SessionState.VERIFYING, SessionState.DEGRADED, SessionState.FAILED,
    },
    SessionState.VERIFYING: {
        SessionState.COMPLETED, SessionState.DEGRADED, SessionState.FAILED,
    },
    SessionState.COMPLETED: set(),
    SessionState.DEGRADED: set(),
    SessionState.FAILED: set(),
    SessionState.CANCELLED: set(),
}


@dataclass(frozen=True, slots=True)
class ConsentEvidence:
    participant_ref: str
    provider: str
    provider_account_id: str
    event_id: str
    policy_version: str
    consent_method: str
    evidence_digest: str
    occurred_at: datetime

    def __post_init__(self) -> None:
        for name in (
            "participant_ref", "provider", "provider_account_id", "event_id",
            "policy_version", "consent_method", "evidence_digest",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"consent evidence {name} must not be empty")
        BridgeSession._require_ref(self.participant_ref)
        if self.occurred_at.tzinfo is None:
            raise ValueError("consent evidence timestamp must be timezone-aware")

    def to_dict(self) -> dict[str, str]:
        return {
            "participant_ref": self.participant_ref,
            "provider": self.provider,
            "provider_account_id": self.provider_account_id,
            "event_id": self.event_id,
            "policy_version": self.policy_version,
            "consent_method": self.consent_method,
            "evidence_digest": self.evidence_digest,
            "occurred_at": self.occurred_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, value: dict[str, str]) -> ConsentEvidence:
        return cls(
            participant_ref=value["participant_ref"],
            provider=value["provider"],
            provider_account_id=value["provider_account_id"],
            event_id=value["event_id"],
            policy_version=value["policy_version"],
            consent_method=value["consent_method"],
            evidence_digest=value["evidence_digest"],
            occurred_at=datetime.fromisoformat(value["occurred_at"]),
        )


@dataclass(frozen=True, slots=True)
class BridgeSession:
    session_id: str
    expected_participants: int
    expected_participant_refs: frozenset[str]
    state: SessionState = SessionState.CREATED
    joined_participants: frozenset[str] = field(default_factory=frozenset)
    consented_participants: frozenset[str] = field(default_factory=frozenset)
    consent_evidence: tuple[ConsentEvidence, ...] = field(default_factory=tuple)
    failure_code: str | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.session_id, str) or not self.session_id.strip():
            raise ValueError("session_id must be a non-empty string")
        if (
            isinstance(self.expected_participants, bool)
            or not isinstance(self.expected_participants, int)
            or self.expected_participants < 2
        ):
            raise ValueError("a bridge requires an integer participant count of at least two")
        if not isinstance(self.expected_participant_refs, frozenset):
            raise ValueError("expected_participant_refs must be an immutable set")
        if not isinstance(self.joined_participants, frozenset) or not isinstance(self.consented_participants, frozenset):
            raise ValueError("joined and consented participants must be immutable sets")
        if not isinstance(self.consent_evidence, tuple):
            raise ValueError("consent_evidence must be an immutable tuple")
        if len(self.expected_participant_refs) != self.expected_participants:
            raise ValueError("expected participant references must match expected_participants")
        for participant_ref in self.expected_participant_refs:
            self._require_ref(participant_ref)
        if not self.joined_participants.issubset(self.expected_participant_refs):
            raise InvalidParticipant("joined participant is not expected for this session")
        if not self.consented_participants.issubset(self.expected_participant_refs):
            raise InvalidParticipant("consented participant is not expected for this session")
        if not self.joined_participants.issubset(self.consented_participants):
            raise ConsentRequired("participants can join only after affirmative consent")
        evidence_refs = [record.participant_ref for record in self.consent_evidence]
        if len(evidence_refs) != len(set(evidence_refs)):
            raise ValueError("each participant may have only one consent evidence record")
        if set(evidence_refs) != set(self.consented_participants):
            raise ValueError("consented participants must have matching durable consent evidence")
        if len(self.joined_participants) > self.expected_participants:
            raise ValueError("too many joined participants")
        if self.state in {
            SessionState.PARTICIPANTS_JOINING, SessionState.RECORDING,
            SessionState.FINALIZING, SessionState.VERIFYING,
            SessionState.COMPLETED, SessionState.DEGRADED,
        } and not self.all_participants_consented:
            raise ConsentRequired("active provider phases require pre-join consent from every expected participant")

    @property
    def all_participants_joined(self) -> bool:
        return self.joined_participants == self.expected_participant_refs

    @property
    def all_participants_consented(self) -> bool:
        return self.consented_participants == self.expected_participant_refs

    def transition(
        self,
        target: SessionState,
        *,
        failure_code: str | None = None,
        at: datetime | None = None,
    ) -> BridgeSession:
        if target is SessionState.PARTICIPANTS_JOINING and not self.all_participants_consented:
            raise ConsentRequired("every expected participant must consent before provider joins")
        if target is SessionState.RECORDING and not self.all_participants_consented:
            raise ConsentRequired(
                "recording requires affirmative pre-join consent from every expected participant"
            )
        if target not in _ALLOWED[self.state]:
            raise InvalidTransition(f"{self.state.value} -> {target.value} is not allowed")
        if target is SessionState.FAILED and not failure_code:
            raise ValueError("failed sessions require a stable failure code")
        return replace(self, state=target, failure_code=failure_code, updated_at=at)

    def participant_consented(
        self,
        participant_ref: str,
        *,
        provider: str,
        provider_account_id: str,
        event_id: str,
        policy_version: str,
        consent_method: str,
        evidence_digest: str,
        at: datetime | None = None,
    ) -> BridgeSession:
        self._require_ref(participant_ref)
        if participant_ref not in self.expected_participant_refs:
            raise InvalidParticipant("consenting participant is not expected for this session")
        # A replay under a new provider event ID is idempotent even after the
        # final consent has advanced the session into PARTICIPANTS_JOINING.
        if participant_ref in self.consented_participants:
            return self
        if self.state not in {SessionState.BRIDGE_LEG_RINGING, SessionState.AWAITING_CONSENT}:
            raise InvalidTransition("consent is accepted only during the pre-join consent phase")
        if at is None:
            raise ValueError("consent evidence requires a provider event timestamp")
        evidence = ConsentEvidence(
            participant_ref=participant_ref,
            provider=provider,
            provider_account_id=provider_account_id,
            event_id=event_id,
            policy_version=policy_version,
            consent_method=consent_method,
            evidence_digest=evidence_digest,
            occurred_at=at,
        )
        updated = replace(
            self,
            consented_participants=self.consented_participants | {participant_ref},
            consent_evidence=self.consent_evidence + (evidence,),
            updated_at=at,
        )
        if updated.all_participants_consented:
            return updated.transition(SessionState.PARTICIPANTS_JOINING, at=at)
        return updated

    def participant_joined(
        self,
        participant_ref: str,
        *,
        at: datetime | None = None,
    ) -> BridgeSession:
        self._require_ref(participant_ref)
        if participant_ref not in self.expected_participant_refs:
            raise InvalidParticipant("joined participant is not expected for this session")
        if self.state not in {SessionState.PARTICIPANTS_JOINING, SessionState.RECORDING}:
            raise InvalidTransition(f"participants cannot join while {self.state.value}")
        if participant_ref not in self.consented_participants:
            raise ConsentRequired("participant must affirmatively consent before joining")
        if participant_ref in self.joined_participants:
            return self
        return replace(
            self,
            joined_participants=self.joined_participants | {participant_ref},
            updated_at=at,
        )

    @staticmethod
    def _require_ref(value: str) -> None:
        if (
            not isinstance(value, str)
            or not value
            or value != value.strip()
            or any(character.isspace() for character in value)
            or len(value) > 128
        ):
            raise InvalidParticipant("a valid opaque participant reference is required")
