from __future__ import annotations
import os
import struct
import tempfile
import wave
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
from bridge_core.address_vault import EncryptedParticipantAddressCodec, PostgresParticipantAddressResolver

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

    def test_encrypted_address_vault_round_trip_is_tenant_scoped(self):
        resolver = PostgresParticipantAddressResolver(
            connect=self.connect,
            codec=EncryptedParticipantAddressCodec(key=b"v" * 32),
        )
        resolver.store(tenant_id="tenant-a", participant_ref="participant-1", address="+15555550123")
        self.assertEqual(
            resolver.resolve(tenant_id="tenant-a", participant_ref="participant-1"),
            "+15555550123",
        )
        with self.assertRaises(LookupError):
            resolver.resolve(tenant_id="tenant-b", participant_ref="participant-1")
        resolver.delete(tenant_id="tenant-a", participant_ref="participant-1")
        with self.assertRaises(LookupError):
            resolver.resolve(tenant_id="tenant-a", participant_ref="participant-1")

    def test_tenant_scope_hides_sessions_from_other_tenants(self):
        self.repo.create_session(BridgeSession(
            "tenant-private-session", 2,
            expected_participant_refs=frozenset({"tenant-a-p1", "tenant-a-p2"}),
            state=SessionState.CREATED,
        ), tenant_id="tenant-a")
        self.assertIsNotNone(self.repo.get_session("tenant-private-session", tenant_id="tenant-a"))
        self.assertIsNone(self.repo.get_session("tenant-private-session", tenant_id="tenant-b"))

    def test_session_cancellation_is_tenant_scoped_and_pre_provider_only(self):
        self.repo.create_session(BridgeSession(
            "tenant-cancel-session", 2,
            expected_participant_refs=frozenset({"cancel-a", "cancel-b"}),
            state=SessionState.CREATED,
        ), tenant_id="tenant-a")
        with self.assertRaises(KeyError):
            self.repo.cancel_session("tenant-cancel-session", tenant_id="tenant-b")
        cancelled = self.repo.cancel_session("tenant-cancel-session", tenant_id="tenant-a")
        self.assertEqual(cancelled.state, SessionState.CANCELLED)
        self.assertIsNotNone(cancelled.updated_at)

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


    def test_s3_success_then_database_failure_is_scheduled_for_recovery(self):
        from providers.twilio.media import TwilioRecordingMediaIngestor
        from bridge_core.object_storage import StoredMediaObject

        class Store:
            def __init__(self):
                self.deleted = []
                self.uploaded = False
                self.fail_delete = False

            @staticmethod
            def _key(*, tenant_id, session_id, media_id):
                return f"test/{tenant_id}/{session_id}/{media_id}"

            def delete(self, **kwargs):
                self.deleted.append(kwargs)
                if self.fail_delete:
                    raise RuntimeError("simulated object cleanup failure")

            def put_wav(self, **kwargs):
                self.uploaded = True
                return StoredMediaObject(
                    object_key="test/object.wav", byte_count=32044,
                    sha256="a" * 64, duration_seconds=1.0,
                    sample_rate_hz=8000, channel_count=2,
                )

        class Resolver:
            @staticmethod
            def expected_participants(_session_id):
                return ("participant-a", "participant-b")

        store = Store()
        ingestor = TwilioRecordingMediaIngestor(
            account_sid="AC" + "c" * 32, api_username="key", api_password="secret",
            provider_account_id="account-test", connect=self.connect,
            resource_resolver=Resolver(), object_store=store,
        )
        recording_sid = "RE" + "c" * 32
        token = ingestor._claim(recording_sid, self.session.session_id, "tenant-test")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp:
            source_path = temp.name
        try:
            with wave.open(source_path, "wb") as output:
                output.setnchannels(2)
                output.setsampwidth(2)
                output.setframerate(8000)
                frames = bytearray()
                for _ in range(8000):
                    frames.extend(struct.pack("<hh", 6000, 7000))
                output.writeframes(bytes(frames))
            ingestor._download = lambda _sid: Path(source_path)

            def fail_database_commit(**_kwargs):
                raise RuntimeError("simulated database commit failure")

            ingestor._commit_asset = fail_database_commit
            with self.assertRaisesRegex(RuntimeError, "simulated database commit failure"):
                ingestor._process_claim(
                    recording_sid=recording_sid, session_id=self.session.session_id,
                    tenant_id="tenant-test", claim_token=token,
                )
        finally:
            Path(source_path).unlink(missing_ok=True)
        self.assertTrue(store.uploaded)
        self.assertEqual(store.deleted, [])
        with self.connect() as conn:
            row = conn.execute(
                """SELECT state, cleanup_required, last_error
                   FROM media_ingestions WHERE provider='twilio'
                     AND provider_account_id='account-test'
                     AND provider_recording_sid=%s""",
                (recording_sid,),
            ).fetchone()
        self.assertEqual(row, ("retry", True, "RuntimeError"))

        store.fail_delete = True
        with self.connect() as conn:
            conn.execute(
                """UPDATE media_ingestions SET next_attempt_at=now()-interval '1 second'
                   WHERE provider='twilio' AND provider_account_id='account-test'
                     AND provider_recording_sid=%s""",
                (recording_sid,),
            )
        with self.assertRaisesRegex(RuntimeError, "simulated object cleanup failure"):
            ingestor.recover_once(limit=1)
        self.assertEqual(len(store.deleted), 1)
        with self.connect() as conn:
            row = conn.execute(
                """SELECT state, cleanup_required, attempts
                   FROM media_ingestions WHERE provider='twilio'
                     AND provider_account_id='account-test'
                     AND provider_recording_sid=%s""",
                (recording_sid,),
            ).fetchone()
        self.assertEqual(row, ("retry", True, 2))



    def test_media_ingestion_claim_is_exclusive_under_concurrency(self):
        from providers.twilio.media import TwilioRecordingMediaIngestor

        class Store:
            @staticmethod
            def _key(*, tenant_id, session_id, media_id):
                return f"test/{tenant_id}/{session_id}/{media_id}"

        ingestor = TwilioRecordingMediaIngestor(
            account_sid="AC" + "a" * 32, api_username="key", api_password="secret",
            provider_account_id="account-test", connect=self.connect,
            resource_resolver=None, object_store=Store(),
        )
        barrier = threading.Barrier(2)

        def claim(_):
            barrier.wait()
            return ingestor._claim("RE" + "a" * 32, self.session.session_id, "tenant-test")

        with ThreadPoolExecutor(max_workers=2) as pool:
            claims = list(pool.map(claim, range(2)))
        self.assertEqual(sum(token is not None for token in claims), 1)
        with self.connect() as conn:
            row = conn.execute(
                """SELECT state, attempts FROM media_ingestions
                   WHERE provider='twilio' AND provider_account_id='account-test'
                     AND provider_recording_sid=%s""",
                ("RE" + "a" * 32,),
            ).fetchone()
        self.assertEqual(row, ("processing", 1))

    def test_expired_media_ingestion_lease_can_be_reclaimed(self):
        from providers.twilio.media import TwilioRecordingMediaIngestor

        class Store:
            @staticmethod
            def _key(*, tenant_id, session_id, media_id):
                return f"test/{tenant_id}/{session_id}/{media_id}"

        ingestor = TwilioRecordingMediaIngestor(
            account_sid="AC" + "b" * 32, api_username="key", api_password="secret",
            provider_account_id="account-test", connect=self.connect,
            resource_resolver=None, object_store=Store(),
        )
        recording_sid = "RE" + "b" * 32
        first = ingestor._claim(recording_sid, self.session.session_id, "tenant-test")
        self.assertIsNotNone(first)
        with self.connect() as conn:
            conn.execute(
                """UPDATE media_ingestions SET lease_expires_at=now()-interval '1 second'
                   WHERE provider='twilio' AND provider_account_id='account-test'
                     AND provider_recording_sid=%s""",
                (recording_sid,),
            )
        second = ingestor._claim(recording_sid, self.session.session_id, "tenant-test")
        self.assertIsNotNone(second)
        self.assertNotEqual(first, second)
        with self.connect() as conn:
            row = conn.execute(
                """SELECT state, attempts, claim_token FROM media_ingestions
                   WHERE provider='twilio' AND provider_account_id='account-test'
                     AND provider_recording_sid=%s""",
                (recording_sid,),
            ).fetchone()
        self.assertEqual(row[0], "processing")
        self.assertEqual(row[1], 2)
        self.assertEqual(str(row[2]), second)


if __name__ == "__main__":
    unittest.main()
