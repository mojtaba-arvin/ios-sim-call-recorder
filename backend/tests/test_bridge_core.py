from __future__ import annotations
import unittest
from datetime import datetime, timezone
from typing import Mapping
from bridge_core.domain import BridgeSession, ConsentRequired, EventType, InvalidParticipant, InvalidTransition, SessionState
from bridge_core.memory import InMemoryBridgeRepository
from bridge_core.webhooks import InvalidWebhookSignature, NormalizedProviderEvent, WebhookProcessor

class StaticVerifier:
    def __init__(self, accepted: bool = True): self.accepted, self.calls = accepted, 0
    def verify(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        self.calls += 1
        return self.accepted and bool(raw_body) and headers.get("X-Test-Signature") == "valid"

class BridgeCoreTests(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryBridgeRepository()
        self.repo.add_session(BridgeSession("session-opaque-1", 2, state=SessionState.AWAITING_USER_ACTION))
        self.verifier = StaticVerifier()
        self.processor = WebhookProcessor(verifier=self.verifier, repository=self.repo)
        self.now = datetime(2026, 11, 19, tzinfo=timezone.utc)

    def event(self, event_id, kind, participant_ref=None, occurred_at=None):
        return NormalizedProviderEvent("test-provider", event_id, "session-opaque-1", kind,
                                        occurred_at or self.now, participant_ref, "sha256:fixture")

    def send(self, event):
        return self.processor.process(raw_body=b'{"synthetic":"event"}',
            headers={"X-Test-Signature": "valid"}, decode=lambda raw: event)

    def test_consent_is_required_before_recording(self):
        session = BridgeSession("s", 2, state=SessionState.AWAITING_CONSENT,
                                joined_participants=frozenset({"p1", "p2"}))
        with self.assertRaises(ConsentRequired): session.transition(SessionState.RECORDING)

    def test_all_participants_join_and_consent_before_recording(self):
        self.send(self.event("1", EventType.BRIDGE_RINGING))
        self.send(self.event("2", EventType.PARTICIPANT_JOINED, "a"))
        self.send(self.event("3", EventType.PARTICIPANT_JOINED, "b"))
        self.assertEqual(self.repo.get_session("session-opaque-1").state, SessionState.AWAITING_CONSENT)
        self.send(self.event("4", EventType.PARTICIPANT_CONSENTED, "a"))
        with self.assertRaises(ConsentRequired): self.send(self.event("5", EventType.RECORDING_STARTED))
        self.send(self.event("6", EventType.PARTICIPANT_CONSENTED, "b"))
        self.send(self.event("7", EventType.RECORDING_STARTED))
        self.assertEqual(self.repo.get_session("session-opaque-1").state, SessionState.RECORDING)

    def test_duplicate_provider_event_is_applied_once(self):
        event = self.event("same-id", EventType.BRIDGE_RINGING)
        self.assertTrue(self.send(event)); self.assertFalse(self.send(event))
        self.assertEqual(self.repo.get_session("session-opaque-1").state, SessionState.BRIDGE_LEG_RINGING)

    def test_invalid_signature_is_rejected_before_decode(self):
        decoded = []
        with self.assertRaises(InvalidWebhookSignature):
            self.processor.process(raw_body=b"tampered", headers={"X-Test-Signature":"invalid"},
                                   decode=lambda raw: decoded.append(raw))
        self.assertEqual(decoded, [])
        self.assertEqual(self.repo.get_session("session-opaque-1").state, SessionState.AWAITING_USER_ACTION)

    def test_late_event_cannot_resurrect_cancelled_session(self):
        session = self.repo.get_session("session-opaque-1")
        self.repo.set_session_for_test(session.transition(SessionState.CANCELLED))
        with self.assertRaises(InvalidTransition): self.send(self.event("late", EventType.BRIDGE_RINGING))
        self.assertEqual(self.repo.get_session("session-opaque-1").state, SessionState.CANCELLED)

    def test_call_end_before_recording_fails_closed(self):
        self.send(self.event("ended", EventType.CALL_ENDED))
        session = self.repo.get_session("session-opaque-1")
        self.assertEqual(session.state, SessionState.FAILED)
        self.assertEqual(session.failure_code, "call_ended_before_recording")

    def test_recording_must_be_finalized_and_verified(self):
        for event in [
            self.event("ring", EventType.BRIDGE_RINGING),
            self.event("ja", EventType.PARTICIPANT_JOINED, "a"),
            self.event("jb", EventType.PARTICIPANT_JOINED, "b"),
            self.event("ca", EventType.PARTICIPANT_CONSENTED, "a"),
            self.event("cb", EventType.PARTICIPANT_CONSENTED, "b"),
            self.event("start", EventType.RECORDING_STARTED),
            self.event("end", EventType.CALL_ENDED),
        ]: self.send(event)
        self.assertEqual(self.repo.get_session("session-opaque-1").state, SessionState.FINALIZING)
        self.send(self.event("ready", EventType.RECORDING_READY))
        self.assertEqual(self.repo.get_session("session-opaque-1").state, SessionState.VERIFYING)
        with self.assertRaises(InvalidTransition): self.send(self.event("late", EventType.RECORDING_STARTED))

    def test_naive_event_timestamp_is_rejected(self):
        with self.assertRaises(ValueError):
            self.event("naive", EventType.BRIDGE_RINGING, occurred_at=datetime(2026, 11, 19))

    def test_unknown_participant_cannot_consent(self):
        self.send(self.event("ring", EventType.BRIDGE_RINGING))
        self.send(self.event("ja", EventType.PARTICIPANT_JOINED, "a"))
        self.send(self.event("jb", EventType.PARTICIPANT_JOINED, "b"))
        with self.assertRaises(InvalidParticipant):
            self.send(self.event("cx", EventType.PARTICIPANT_CONSENTED, "unknown"))

    def test_out_of_order_event_cannot_override_later_state(self):
        for event in [
            self.event("ring", EventType.BRIDGE_RINGING),
            self.event("ja", EventType.PARTICIPANT_JOINED, "a"),
            self.event("jb", EventType.PARTICIPANT_JOINED, "b"),
            self.event("ca", EventType.PARTICIPANT_CONSENTED, "a"),
            self.event("cb", EventType.PARTICIPANT_CONSENTED, "b"),
            self.event("start", EventType.RECORDING_STARTED),
            self.event("end", EventType.CALL_ENDED),
        ]: self.send(event)
        late = self.event("late-join", EventType.PARTICIPANT_JOINED, "c",
                          datetime(2026, 11, 18, tzinfo=timezone.utc))
        with self.assertRaises(InvalidTransition): self.send(late)
        self.assertEqual(self.repo.get_session("session-opaque-1").state, SessionState.FINALIZING)

    def test_stale_failure_event_cannot_override_verification_state(self):
        for event in [
            self.event("ring", EventType.BRIDGE_RINGING),
            self.event("ja", EventType.PARTICIPANT_JOINED, "a"),
            self.event("jb", EventType.PARTICIPANT_JOINED, "b"),
            self.event("ca", EventType.PARTICIPANT_CONSENTED, "a"),
            self.event("cb", EventType.PARTICIPANT_CONSENTED, "b"),
            self.event("start", EventType.RECORDING_STARTED),
            self.event("end", EventType.CALL_ENDED),
            self.event("ready", EventType.RECORDING_READY),
        ]: self.send(event)
        stale = self.event("old-failure", EventType.RECORDING_FAILED,
                           occurred_at=datetime(2026, 11, 18, tzinfo=timezone.utc))
        with self.assertRaises(InvalidTransition): self.send(stale)
        self.assertEqual(self.repo.get_session("session-opaque-1").state, SessionState.VERIFYING)

if __name__ == "__main__": unittest.main()
