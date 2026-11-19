from __future__ import annotations

import unittest
from datetime import datetime, timezone

from bridge_core.application import OutboxCommand
from bridge_core.domain import (
    BridgeSession,
    ConsentRequired,
    EventType,
    InvalidParticipant,
    InvalidTransition,
    SessionState,
)
from bridge_core.memory import InMemoryBridgeRepository
from bridge_core.ports import SignedWebhookRequest
from bridge_core.webhooks import InvalidWebhookSignature, NormalizedProviderEvent, WebhookProcessor


class StaticVerifier:
    def __init__(self, accepted: bool = True):
        self.accepted, self.calls = accepted, 0

    def verify(self, request: SignedWebhookRequest) -> bool:
        self.calls += 1
        return (
            self.accepted
            and bool(request.raw_body)
            and request.headers.get("X-Test-Signature") == "valid"
            and request.public_url.startswith("https://")
        )


class BridgeCoreTests(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryBridgeRepository()
        self.expected_refs = frozenset({"a", "b"})
        self.repo.add_session(
            BridgeSession(
                "session-opaque-1",
                2,
                expected_participant_refs=self.expected_refs,
                state=SessionState.AWAITING_USER_ACTION,
            )
        )
        self.verifier = StaticVerifier()
        self.processor = WebhookProcessor(verifier=self.verifier, repository=self.repo)
        self.now = datetime(2026, 11, 19, tzinfo=timezone.utc)

    def event(self, event_id, kind, participant_ref=None, occurred_at=None):
        return NormalizedProviderEvent(
            "test-provider",
            event_id,
            "session-opaque-1",
            kind,
            occurred_at or self.now,
            participant_ref,
            "sha256:fixture",
        )

    def send(self, event):
        request = SignedWebhookRequest(
            method="POST",
            public_url="https://hooks.example.test/provider",
            content_type="application/json",
            raw_body=b'{"synthetic":"event"}',
            headers={"X-Test-Signature": "valid"},
        )
        return self.processor.process(request=request, decode=lambda verified_request: event)

    def preconsent(self):
        self.send(self.event("ring", EventType.BRIDGE_RINGING))
        self.send(self.event("consent-a", EventType.PARTICIPANT_CONSENTED, "a"))
        self.send(self.event("consent-b", EventType.PARTICIPANT_CONSENTED, "b"))

    def test_provider_join_phase_requires_all_preconsents(self):
        session = BridgeSession(
            "s",
            2,
            expected_participant_refs=frozenset({"p1", "p2"}),
            state=SessionState.AWAITING_CONSENT,
            consented_participants=frozenset({"p1"}),
        )
        with self.assertRaises(ConsentRequired):
            session.transition(SessionState.PARTICIPANTS_JOINING)

    def test_consent_is_collected_before_any_conference_participant_joins(self):
        self.send(self.event("ring", EventType.BRIDGE_RINGING))
        self.send(self.event("consent-a", EventType.PARTICIPANT_CONSENTED, "a"))
        self.assertEqual(
            self.repo.get_session("session-opaque-1").state,
            SessionState.BRIDGE_LEG_RINGING,
        )
        self.send(self.event("consent-b", EventType.PARTICIPANT_CONSENTED, "b"))
        session = self.repo.get_session("session-opaque-1")
        self.assertEqual(session.state, SessionState.PARTICIPANTS_JOINING)
        self.assertEqual(session.joined_participants, frozenset())
        with self.assertRaises(ConsentRequired):
            self.send(self.event("recording-before-consent", EventType.RECORDING_STARTED))

        # Provider recording callbacks can race ahead of the participant-joined
        # callback. Once every participant has pre-consented, the provider's
        # recording.started event is authoritative even if join webhooks lag.
        self.send(self.event("recording-started", EventType.RECORDING_STARTED))
        self.send(self.event("join-a", EventType.PARTICIPANT_JOINED, "a"))
        self.send(self.event("join-b", EventType.PARTICIPANT_JOINED, "b"))
        session = self.repo.get_session("session-opaque-1")
        self.assertEqual(session.state, SessionState.RECORDING)
        self.assertEqual(session.joined_participants, self.expected_refs)
        self.assertTrue(session.all_participants_consented)

    def test_last_consent_enqueues_recording_from_start_conference_creation(self):
        self.send(self.event("ring", EventType.BRIDGE_RINGING))
        self.send(self.event("consent-a", EventType.PARTICIPANT_CONSENTED, "a"))
        self.assertEqual(self.repo.get_outbox_commands(), ())

        self.send(self.event("consent-b", EventType.PARTICIPANT_CONSENTED, "b"))
        commands = self.repo.get_outbox_commands()
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0].command_type, "conference.create")
        self.assertEqual(
            commands[0].payload,
            {"participant_ref": "a", "recording_mode": "from_start"},
        )
        self.send(self.event("consent-b-replayed", EventType.PARTICIPANT_CONSENTED, "b"))
        self.assertEqual(len(self.repo.get_outbox_commands()), 1)

    def test_first_join_enqueues_only_remaining_preconsented_participants(self):
        self.preconsent()
        self.send(self.event("join-a", EventType.PARTICIPANT_JOINED, "a"))
        commands = self.repo.get_outbox_commands()
        self.assertEqual(len(commands), 2)
        add_commands = [command for command in commands if command.command_type == "participant.add"]
        self.assertEqual(len(add_commands), 1)
        self.assertEqual(add_commands[0].payload, {"participant_ref": "b"})

        # A duplicate join with a different provider event ID regenerates the
        # same idempotency key and cannot create a second participant command.
        self.send(self.event("join-a-replayed", EventType.PARTICIPANT_JOINED, "a"))
        self.assertEqual(len(self.repo.get_outbox_commands()), 2)

    def test_participant_cannot_join_before_consent(self):
        self.send(self.event("ring", EventType.BRIDGE_RINGING))
        with self.assertRaises(ConsentRequired):
            self.send(self.event("join-before-consent", EventType.PARTICIPANT_JOINED, "a"))
        self.assertEqual(
            self.repo.get_session("session-opaque-1").joined_participants,
            frozenset(),
        )

    def test_duplicate_provider_event_is_applied_once(self):
        event = self.event("same-id", EventType.BRIDGE_RINGING)
        self.assertTrue(self.send(event))
        self.assertFalse(self.send(event))
        self.assertEqual(
            self.repo.get_session("session-opaque-1").state,
            SessionState.BRIDGE_LEG_RINGING,
        )

    def test_invalid_signature_is_rejected_before_decode(self):
        decoded = []
        with self.assertRaises(InvalidWebhookSignature):
            self.processor.process(
                request=SignedWebhookRequest(
                    method="POST",
                    public_url="https://hooks.example.test/provider",
                    content_type="application/json",
                    raw_body=b"tampered",
                    headers={"X-Test-Signature": "invalid"},
                ),
                decode=lambda verified_request: decoded.append(verified_request),
            )
        self.assertEqual(decoded, [])
        self.assertEqual(
            self.repo.get_session("session-opaque-1").state,
            SessionState.AWAITING_USER_ACTION,
        )

    def test_outbox_payload_rejects_sensitive_fields_and_telephony_aliases(self):
        forbidden_keys = (
            "phone_number", "from", "to", "source", "destination", "caller",
            "callee", "number", "from_number", "to_number",
            "destination_number", "e164", "telephone",
        )
        for key in forbidden_keys:
            with self.subTest(key=key), self.assertRaises(ValueError):
                OutboxCommand(
                    command_type="conference.create",
                    idempotency_key=f"unsafe-{key}",
                    session_id="session-opaque-1",
                    provider="test-provider",
                    payload={"nested": [{"metadata": {key: "+15555550123}}]},
                )

    def test_decoder_receives_the_exact_verified_request(self):
        event = self.event("same-request", EventType.BRIDGE_RINGING)
        request = SignedWebhookRequest(
            method="POST",
            public_url="https://hooks.example.test/provider",
            content_type="application/x-www-form-urlencoded",
            raw_body=b"event=ring",
            headers={"X-Test-Signature": "valid"},
            form_parameters={"event": "ring"},
        )
        decoded = []
        self.processor.process(
            request=request,
            decode=lambda verified_request: (decoded.append(verified_request) or event),
        )
        self.assertEqual(len(decoded), 1)
        self.assertIs(decoded[0], request)

    def test_late_event_cannot_resurrect_cancelled_session(self):
        session = self.repo.get_session("session-opaque-1")
        self.repo.set_session_for_test(session.transition(SessionState.CANCELLED))
        with self.assertRaises(InvalidTransition):
            self.send(self.event("late", EventType.BRIDGE_RINGING))
        self.assertEqual(
            self.repo.get_session("session-opaque-1").state,
            SessionState.CANCELLED,
        )

    def test_call_end_before_recording_fails_closed(self):
        self.send(self.event("ended", EventType.CALL_ENDED))
        session = self.repo.get_session("session-opaque-1")
        self.assertEqual(session.state, SessionState.FAILED)
        self.assertEqual(session.failure_code, "call_ended_before_recording")

    def test_recording_must_be_finalized_and_verified(self):
        self.preconsent()
        self.send(self.event("join-a", EventType.PARTICIPANT_JOINED, "a"))
        self.send(self.event("start", EventType.RECORDING_STARTED))
        self.send(self.event("end", EventType.CALL_ENDED))
        self.assertEqual(
            self.repo.get_session("session-opaque-1").state,
            SessionState.FINALIZING,
        )
        self.send(self.event("ready", EventType.RECORDING_READY))
        self.assertEqual(
            self.repo.get_session("session-opaque-1").state,
            SessionState.VERIFYING,
        )
        with self.assertRaises(InvalidTransition):
            self.send(self.event("late", EventType.RECORDING_STARTED))

    def test_naive_event_timestamp_is_rejected(self):
        with self.assertRaises(ValueError):
            self.event(
                "naive",
                EventType.BRIDGE_RINGING,
                occurred_at=datetime(2026, 11, 19),
            )

    def test_unknown_participant_cannot_consent(self):
        self.send(self.event("ring", EventType.BRIDGE_RINGING))
        with self.assertRaises(InvalidParticipant):
            self.send(self.event("consent-unknown", EventType.PARTICIPANT_CONSENTED, "unknown"))

    def test_out_of_order_event_cannot_override_later_state(self):
        self.preconsent()
        self.send(self.event("join-a", EventType.PARTICIPANT_JOINED, "a"))
        self.send(self.event("start", EventType.RECORDING_STARTED))
        self.send(self.event("end", EventType.CALL_ENDED))
        late = self.event(
            "late-join",
            EventType.PARTICIPANT_JOINED,
            "b",
            datetime(2026, 11, 18, tzinfo=timezone.utc),
        )
        with self.assertRaises(InvalidTransition):
            self.send(late)
        self.assertEqual(
            self.repo.get_session("session-opaque-1").state,
            SessionState.FINALIZING,
        )

    def test_stale_failure_event_cannot_override_verification_state(self):
        self.preconsent()
        self.send(self.event("join-a", EventType.PARTICIPANT_JOINED, "a"))
        self.send(self.event("start", EventType.RECORDING_STARTED))
        self.send(self.event("end", EventType.CALL_ENDED))
        self.send(self.event("ready", EventType.RECORDING_READY))
        stale = self.event(
            "old-failure",
            EventType.RECORDING_FAILED,
            occurred_at=datetime(2026, 11, 18, tzinfo=timezone.utc),
        )
        with self.assertRaises(InvalidTransition):
            self.send(stale)
        self.assertEqual(
            self.repo.get_session("session-opaque-1").state,
            SessionState.VERIFYING,
        )


if __name__ == "__main__":
    unittest.main()
