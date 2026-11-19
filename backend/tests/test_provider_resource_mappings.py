from __future__ import annotations

import os
import unittest
from pathlib import Path

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

from bridge_core.domain import BridgeSession, SessionState
from bridge_core.persistence import ProviderResourceConflict, PostgresBridgeRepository


DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
_SKIP = psycopg is None or not DATABASE_URL


@unittest.skipIf(_SKIP, "TEST_DATABASE_URL and psycopg are required for PostgreSQL integration tests")
class ProviderResourceMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.connect = staticmethod(lambda: psycopg.connect(DATABASE_URL))
        migrations = Path(__file__).parents[1] / "migrations"
        with cls.connect() as conn:
            conn.execute((migrations / "0001_bridge_persistence.sql").read_text())
            conn.execute((migrations / "0002_provider_resources.sql").read_text())

    def setUp(self):
        with self.connect() as conn:
            conn.execute(
                "TRUNCATE provider_participant_resources, provider_resources, "
                "outbox_commands, provider_event_receipts, bridge_sessions CASCADE"
            )
        self.repo = PostgresBridgeRepository(self.connect)
        self.repo.create_session(BridgeSession(
            "mapping-session", 2, state=SessionState.AWAITING_USER_ACTION,
        ))

    def test_conference_mapping_is_scoped_and_immutable(self):
        self.repo.put_provider_resource(
            "twilio", "account-a", "mapping-session", "CF" + "a" * 32,
        )
        self.assertEqual(
            self.repo.get_provider_resource("twilio", "account-a", "mapping-session"),
            "CF" + "a" * 32,
        )
        with self.assertRaises(ProviderResourceConflict):
            self.repo.put_provider_resource(
                "twilio", "account-a", "mapping-session", "CF" + "b" * 32,
            )

    def test_same_provider_sid_cannot_be_owned_by_two_sessions_in_one_account(self):
        self.repo.put_provider_resource(
            "twilio", "account-a", "mapping-session", "CF" + "c" * 32,
        )
        self.repo.create_session(BridgeSession(
            "other-session", 2, state=SessionState.AWAITING_USER_ACTION,
        ))
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self.repo.put_provider_resource(
                "twilio", "account-a", "other-session", "CF" + "c" * 32,
            )

    def test_participant_call_sid_is_scoped_to_opaque_participant_reference(self):
        self.repo.put_provider_resource(
            "twilio", "account-a", "mapping-session", "CF" + "d" * 32,
        )
        self.repo.put_provider_participant_resource(
            "twilio", "account-a", "mapping-session",
            "participant-opaque-1", "CA" + "e" * 32,
        )
        self.assertEqual(
            self.repo.get_provider_participant_resource(
                "twilio", "account-a", "mapping-session", "participant-opaque-1",
            ),
            "CA" + "e" * 32,
        )
        self.assertIsNone(self.repo.get_provider_participant_resource(
            "twilio", "account-b", "mapping-session", "participant-opaque-1",
        ))


if __name__ == "__main__":
    unittest.main()
