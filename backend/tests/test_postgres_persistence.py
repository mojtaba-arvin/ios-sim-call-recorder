from __future__ import annotations
import os
import threading
import time
import unittest
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4
try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None
from bridge_core.application import EventApplication, OutboxCommand
from bridge_core.domain import BridgeSession, SessionState
from bridge_core.persistence import CommandIdentityConflict, EventIdentityConflict, LeaseLost, PostgresBridgeRepository

DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
_SKIP = psycopg is None or not DATABASE_URL

@unittest.skipIf(_SKIP, "TEST_DATABASE_URL and psycopg are required for PostgreSQL integration tests")
class PostgresPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.connect = staticmethod(lambda: psycopg.connect(DATABASE_URL))
        migrations = Path(__file__).parents[1] / "migrations"
        with cls.connect() as conn:
            for migration in sorted(migrations.glob("*.sql")):
                conn.execute(migration.read_text())

    def setUp(self):
        with self.connect() as conn:
            conn.execute("TRUNCATE outbox_commands, provider_event_receipts, bridge_sessions CASCADE")
        self.repo = PostgresBridgeRepository(self.connect)
        self.session = BridgeSession(
            "session-test", 2,
            expected_participant_refs=frozenset({"participant-a", "participant-b"}),
            state=SessionState.AWAITING_USER_ACTION,
        )
        self.repo.create_session(self.session)

    def command(self, key=None):
        return OutboxCommand("recording.start", key or f"recording-start:{uuid4()}",
                             self.session.session_id, "twilio", "account-test",
                             {"session_id": self.session.session_id})

    def test_expected_participant_references_round_trip_through_postgres(self):
        loaded = self.repo.get_session(self.session.session_id)
        self.assertEqual(loaded.expected_participant_refs, self.session.expected_participant_refs)


    def test_consent_evidence_round_trips_with_provider_event_and_policy(self):
        ringing = self.session.transition(SessionState.BRIDGE_LEG_RINGING)
        self.repo.apply_event_once(
            "twilio", "bridge-ringing", self.session.session_id,
            lambda _: ringing, provider_account_id="account-test",
        )
        current = self.repo.get_session(self.session.session_id)
        updated = current.participant_consented(
            "participant-a",
            provider="twilio",
            provider_account_id="account-test",
            event_id="consent-a",
            policy_version="consent-v1",
            consent_method="dtmf",
            evidence_digest="sha256:consent-evidence",
            at=datetime(2026, 11, 19, tzinfo=timezone.utc),
        )
        self.repo.apply_event_once(
            "twilio", "consent-a", self.session.session_id,
            lambda _: updated,
            provider_account_id="account-test",
            payload_digest="sha256:consent-evidence",
        )
        loaded = self.repo.get_session(self.session.session_id)
        self.assertEqual(loaded.consented_participants, frozenset({"participant-a"}))
        self.assertEqual(len(loaded.consent_evidence), 1)
        evidence = loaded.consent_evidence[0]
        self.assertEqual(evidence.event_id, "consent-a")
        self.assertEqual(evidence.policy_version, "consent-v1")
        self.assertEqual(evidence.consent_method, "dtmf")
        self.assertEqual(evidence.evidence_digest, "sha256:consent-evidence")

    def test_event_receipt_session_and_outbox_commit_atomically(self):
        command = self.command("recording-start:atomic")
        updated = self.session.transition(SessionState.BRIDGE_LEG_RINGING)
        self.assertTrue(self.repo.apply_event_once(
            "twilio", "event-atomic", self.session.session_id,
            lambda _: EventApplication(updated, (command,)), provider_account_id="account-test"))
        self.assertEqual(self.repo.get_session(self.session.session_id).state, SessionState.BRIDGE_LEG_RINGING)
        claimed = self.repo.claim_outbox(worker_id="worker-a", limit=1)
        self.assertEqual(len(claimed), 1)
        self.assertEqual(claimed[0].idempotency_key, command.idempotency_key)

    def test_failed_transition_rolls_back_event_receipt_and_session(self):
        def fail(_):
            raise RuntimeError("synthetic failure")
        with self.assertRaises(RuntimeError):
            self.repo.apply_event_once("twilio", "event-rollback", self.session.session_id,
                                       fail, provider_account_id="account-test")
        with self.connect() as conn:
            count = conn.execute("SELECT count(*) FROM provider_event_receipts WHERE event_id = %s",
                                 ("event-rollback",)).fetchone()[0]
        self.assertEqual(count, 0)
        self.assertEqual(self.repo.get_session(self.session.session_id).state,
                         SessionState.AWAITING_USER_ACTION)

    def test_outbox_insert_failure_rolls_back_receipt_and_session_update(self):
        updated = self.session.transition(SessionState.BRIDGE_LEG_RINGING)
        wrong_session_command = OutboxCommand(
            command_type="recording.start", idempotency_key="wrong-session-command",
            session_id="another-session", provider="twilio", provider_account_id="account-test",
            payload={"session_id": "another-session"},
        )
        with self.assertRaises(ValueError):
            self.repo.apply_event_once(
                "twilio", "event-outbox-rollback", self.session.session_id,
                lambda _: EventApplication(updated, (wrong_session_command,)),
                provider_account_id="account-test",
            )
        self.assertEqual(self.repo.get_session(self.session.session_id).state,
                         SessionState.AWAITING_USER_ACTION)
        with self.connect() as conn:
            receipt_count = conn.execute(
                "SELECT count(*) FROM provider_event_receipts WHERE event_id = %s",
                ("event-outbox-rollback",),
            ).fetchone()[0]
            command_count = conn.execute(
                "SELECT count(*) FROM outbox_commands WHERE idempotency_key = %s",
                ("wrong-session-command",),
            ).fetchone()[0]
        self.assertEqual(receipt_count, 0)
        self.assertEqual(command_count, 0)

    def test_duplicate_event_is_ignored_and_cross_session_reuse_is_rejected(self):
        apply = lambda s: s.transition(SessionState.BRIDGE_LEG_RINGING)
        self.assertTrue(self.repo.apply_event_once("twilio", "same-event", self.session.session_id, apply))
        self.assertFalse(self.repo.apply_event_once("twilio", "same-event", self.session.session_id, apply))
        self.repo.create_session(BridgeSession(
            "other-session", 2,
            expected_participant_refs=frozenset({"other-a", "other-b"}),
            state=SessionState.AWAITING_USER_ACTION,
        ))
        with self.assertRaises(EventIdentityConflict):
            self.repo.apply_event_once("twilio", "same-event", "other-session", apply)
        with self.assertRaises(EventIdentityConflict):
            self.repo.apply_event_once("twilio", "same-event", self.session.session_id,
                                       apply, payload_digest="different-payload")

    def test_idempotency_key_cannot_alias_a_different_command(self):
        original = self.command("same-command-key")
        self.assertTrue(self.repo.enqueue_command(original))
        conflicting = OutboxCommand(
            command_type="recording.stop", idempotency_key=original.idempotency_key,
            session_id=original.session_id, provider=original.provider,
            provider_account_id=original.provider_account_id,
            payload={"session_id": original.session_id},
        )
        with self.assertRaises(CommandIdentityConflict):
            self.repo.enqueue_command(conflicting)

    def test_event_identity_is_scoped_by_provider_account(self):
        apply = lambda s: s
        self.assertTrue(self.repo.apply_event_once("twilio", "same-event", self.session.session_id,
                                                   apply, provider_account_id="account-a"))
        self.assertTrue(self.repo.apply_event_once("twilio", "same-event", self.session.session_id,
                                                   apply, provider_account_id="account-b"))

    def test_concurrent_duplicate_delivery_applies_once(self):
        barrier = threading.Barrier(8)
        count = 0
        count_lock = threading.Lock()
        def deliver():
            nonlocal count
            barrier.wait()
            def apply(session):
                nonlocal count
                with count_lock:
                    count += 1
                return session.transition(SessionState.BRIDGE_LEG_RINGING)
            return self.repo.apply_event_once("twilio", "racing-event", self.session.session_id,
                                              apply, provider_account_id="account-test")
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: deliver(), range(8)))
        self.assertEqual(sum(results), 1)
        self.assertEqual(count, 1)

    def test_workers_never_claim_the_same_command(self):
        for index in range(4):
            self.repo.enqueue_command(self.command(f"worker-race:{index}"))
        barrier = threading.Barrier(2)
        def claim(worker):
            barrier.wait()
            return self.repo.claim_outbox(worker_id=worker, limit=2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = list(pool.map(claim, ("worker-a", "worker-b")))
        first_ids = {item.command_id for item in first}
        second_ids = {item.command_id for item in second}
        self.assertTrue(first_ids)
        self.assertTrue(second_ids)
        self.assertFalse(first_ids & second_ids)

    def test_expired_lease_is_recovered_with_a_new_token(self):
        self.repo.enqueue_command(self.command("lease-expiry"))
        first = self.repo.claim_outbox(worker_id="worker-a", limit=1, lease_seconds=1)[0]
        time.sleep(1.15)
        second = self.repo.claim_outbox(worker_id="worker-b", limit=1, lease_seconds=30)[0]
        self.assertEqual(first.command_id, second.command_id)
        self.assertNotEqual(first.lease_token, second.lease_token)
        with self.assertRaises(LeaseLost):
            self.repo.acknowledge_outbox(first.command_id, first.lease_token)

    def test_retry_is_bounded_and_dead_lettered(self):
        self.repo.enqueue_command(self.command("bounded-retry"))
        first = self.repo.claim_outbox(worker_id="worker-a", limit=1)[0]
        with self.connect() as conn:
            conn.execute("UPDATE outbox_commands SET max_attempts = 2 WHERE command_id = %s",
                         (first.command_id,))
        self.assertEqual(self.repo.fail_outbox(first.command_id, first.lease_token,
                                               error_code="provider_timeout", retry_delay_seconds=0), "pending")
        second = self.repo.claim_outbox(worker_id="worker-b", limit=1)[0]
        self.assertEqual(second.attempts, 2)
        self.assertEqual(self.repo.fail_outbox(second.command_id, second.lease_token,
                                               error_code="provider_timeout", retry_delay_seconds=0), "dead")
        self.assertEqual(self.repo.claim_outbox(worker_id="worker-c", limit=10), ())
        dead = self.repo.list_dead_letters(limit=10)
        self.assertEqual(len(dead), 1)
        self.assertEqual(dead[0].last_error_code, "provider_timeout")
        self.assertEqual(dead[0].attempts, 2)
        self.assertFalse(hasattr(dead[0], "payload"))

    def test_acknowledgement_requires_current_lease_token(self):
        self.repo.enqueue_command(self.command("ack-token"))
        leased = self.repo.claim_outbox(worker_id="worker-a", limit=1)[0]
        with self.assertRaises(LeaseLost):
            self.repo.acknowledge_outbox(leased.command_id, uuid4())
        self.repo.acknowledge_outbox(leased.command_id, leased.lease_token)

    def test_terminal_provider_failure_is_dead_lettered_immediately(self):
        self.repo.enqueue_command(self.command("terminal-provider-error"))
        leased = self.repo.claim_outbox(worker_id="worker-terminal", limit=1)[0]
        status = self.repo.fail_outbox(
            leased.command_id, leased.lease_token,
            error_code="provider_request_rejected",
            retry_delay_seconds=86400,
            terminal=True,
        )
        self.assertEqual(status, "dead")
        self.assertEqual(self.repo.claim_outbox(worker_id="worker-retry", limit=10), ())

if __name__ == "__main__":
    unittest.main()
