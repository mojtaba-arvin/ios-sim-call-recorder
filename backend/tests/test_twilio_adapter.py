from __future__ import annotations

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from bridge_core.persistence import LeasedCommand
from providers.twilio.adapter import TwilioConferenceCommandAdapter
from providers.twilio.consent import build_consent_gather_twiml


ACCOUNT = "AC" + "a" * 32
CALL = "CA" + "b" * 32
CONF = "CF" + "c" * 32


class FakeCalls:
    def __init__(self):
        self.created = []
    def create(self, **kwargs):
        self.created.append(kwargs)
        return SimpleNamespace(sid=CALL)


class FakeParticipants:
    def __init__(self):
        self.created = []
        self.items = []
    def create(self, **kwargs):
        self.created.append(kwargs)
        return SimpleNamespace(call_sid=CALL, conference_sid=CONF)
    def list(self, **kwargs):
        return self.items


class FakeConference:
    def __init__(self):
        self.participants = FakeParticipants()
    def fetch(self):
        return SimpleNamespace(sid=CONF, status="in-progress")
    def update(self, **kwargs):
        return SimpleNamespace(status="completed")


class FakeClient:
    def __init__(self):
        self.calls = FakeCalls()
        self.resources = {}
        self.conferences = self._conference_factory
    def _conference_factory(self, sid):
        return self.resources.setdefault(sid, FakeConference())


def command(kind, payload, *, attempts=1):
    return LeasedCommand(
        command_id=uuid4(), command_type=kind, idempotency_key="idempotency-key",
        session_id="session-123", provider="twilio", provider_account_id="twilio-main",
        payload=payload, attempts=attempts, lease_token=uuid4(), lease_owner="worker",
        lease_expires_at=datetime.now(timezone.utc),
    )


class TwilioAdapterTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeClient()
        self.adapter = TwilioConferenceCommandAdapter(
            client=self.client, account_sid=ACCOUNT, from_number="+14155550100",
            public_origin="https://hooks.example.test",
            consent_disclosure="This call is recorded. Press 1 to agree.",
            address_resolver=lambda session, participant: "+14155550101",
        )

    def test_consent_twiml_escapes_disclosure_and_requires_https(self):
        xml = build_consent_gather_twiml(
            disclosure="Recording & privacy. <Read this>",
            action_url="https://hooks.example.test/v1/twilio/consent",
        )
        self.assertIn("Recording &amp; privacy. &lt;Read this&gt;", xml)
        self.assertIn('numDigits="1"', xml)
        with self.assertRaises(ValueError):
            build_consent_gather_twiml(disclosure="x", action_url="http://insecure.test")

    def test_consent_request_places_real_twilio_calls_api_request(self):
        result = self.adapter.execute(
            command("consent.request", {"participant_ref": "participant-a"}),
            conference_sid=None, call_sid=None,
        )
        self.assertEqual(result.call_sid, CALL)
        self.assertEqual(self.client.calls.created[0]["to"], "+14155550101")
        self.assertIn("<Gather", self.client.calls.created[0]["twiml"])
        self.assertIn("/v1/twilio/consent", self.client.calls.created[0]["twiml"])

    def test_conference_create_requests_record_from_start_and_dual_channels(self):
        result = self.adapter.execute(
            command("conference.create", {
                "participant_ref": "participant-a", "recording_mode": "from_start",
            }),
            conference_sid=None, call_sid=None,
        )
        self.assertEqual(result.conference_sid, CONF)
        self.assertEqual(result.call_sid, CALL)
        args = next(iter(self.client.resources.values())).participants.created[0]
        self.assertEqual(args["conference_record"], "record-from-start")
        self.assertEqual(args["recording_channels"], "dual")
        self.assertEqual(args["label"], "participant-a")

    def test_participant_add_requires_existing_conference(self):
        result = self.adapter.execute(
            command("participant.add", {"participant_ref": "participant-b"}),
            conference_sid=CONF, call_sid=None,
        )
        self.assertEqual(result.conference_sid, CONF)
        args = self.client.resources[CONF].participants.created[0]
        self.assertEqual(args["conference_record"], "record-from-start")
        self.assertEqual(args["label"], "participant-b")

    def test_reconciliation_matches_opaque_participant_label(self):
        resource = self.client.resources.setdefault(CONF, FakeConference())
        resource.participants.items = [SimpleNamespace(label="participant-a", call_sid=CALL)]
        result = self.adapter.reconcile(
            command("participant.add", {"participant_ref": "participant-a"}),
            conference_sid=CONF, call_sid=None,
        )
        self.assertEqual(result.state.value, "applied")
        self.assertEqual(result.call_sid, CALL)

    def test_uncertain_call_creation_is_not_replayed(self):
        result = self.adapter.reconcile(
            command("consent.request", {"participant_ref": "participant-a"}, attempts=2),
            conference_sid=None, call_sid=None,
        )
        self.assertEqual(result.state.value, "unknown")


if __name__ == "__main__":
    unittest.main()
