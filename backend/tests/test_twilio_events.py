from __future__ import annotations

import hashlib
import unittest
from datetime import datetime, timezone

from bridge_core.domain import EventType
from bridge_core.ports import SignedWebhookRequest
from providers.twilio.events import TwilioEventDecodeError, TwilioWebhookEventDecoder


ACCOUNT = "AC" + "a" * 32
CALL = "CA" + "b" * 32
CONFERENCE = "CF" + "c" * 32


class TwilioWebhookEventDecoderTests(unittest.TestCase):
    def setUp(self):
        self.resolutions = []
        self.decoder = TwilioWebhookEventDecoder(
            account_sid=ACCOUNT,
            provider_account_id="twilio-prod-account-opaque",
            consent_policy_version="consent-v1",
            resolve_session=self.resolve,
            clock=lambda: datetime(2026, 11, 20, tzinfo=timezone.utc),
        )

    def resolve(self, call_sid, conference_sid):
        self.resolutions.append((call_sid, conference_sid))
        if call_sid == CALL or conference_sid == CONFERENCE:
            return "session-internal-1", "participant-internal-1"
        raise LookupError("unowned provider resource")

    def request(self, route, fields, *, headers=None):
        raw = "&".join(f"{key}={value}" for key, value in fields.items()).encode()
        return SignedWebhookRequest(
            method="POST",
            public_url=f"https://hooks.example.test/v1/twilio/{route}",
            content_type="application/x-www-form-urlencoded",
            raw_body=raw,
            headers={"content-type": "application/x-www-form-urlencoded", **(headers or {})},
            form_parameters={key: (value,) for key, value in fields.items()},
        )

    def base(self):
        return {"AccountSid": ACCOUNT, "CallSid": CALL}

    def test_consent_requires_affirmative_digit_and_emits_only_opaque_identity(self):
        fields = {**self.base(), "Digits": "1"}
        event = self.decoder(self.request("consent", fields))
        self.assertEqual(event.event_type, EventType.PARTICIPANT_CONSENTED)
        self.assertEqual(event.participant_ref, "participant-internal-1")
        self.assertEqual(event.consent_method, "dtmf_1")
        self.assertEqual(event.consent_policy_version, "consent-v1")
        self.assertEqual(event.provider_account_id, "twilio-prod-account-opaque")
        self.assertNotIn(CALL, repr(event))
        self.assertEqual(len(event.payload_digest), 64)

    def test_non_affirmative_consent_is_normalized_as_decline(self):
        event = self.decoder(
            self.request("consent", {**self.base(), "Digits": "2"})
        )
        self.assertEqual(event.event_type, EventType.PARTICIPANT_DECLINED)
        self.assertEqual(event.participant_ref, "participant-internal-1")

    def test_conference_join_maps_to_participant_joined(self):
        event = self.decoder(self.request("conference", {
            **self.base(), "ConferenceSid": CONFERENCE,
            "StatusCallbackEvent": "participant-join",
        }))
        self.assertEqual(event.event_type, EventType.PARTICIPANT_JOINED)
        self.assertEqual(event.participant_ref, "participant-internal-1")

    def test_conference_participant_leave_is_acknowledged_as_status(self):
        event = self.decoder(self.request("conference", {
            **self.base(), "ConferenceSid": CONFERENCE,
            "StatusCallbackEvent": "participant-leave",
        }))
        self.assertEqual(event.event_type, EventType.PROVIDER_STATUS)

    def test_conference_end_maps_to_call_ended(self):
        event = self.decoder(self.request("conference", {
            **self.base(), "ConferenceSid": CONFERENCE,
            "StatusCallbackEvent": "conference-end",
        }))
        self.assertEqual(event.event_type, EventType.CALL_ENDED)
        self.assertIsNone(event.participant_ref)

    def test_recording_completed_maps_to_ready_without_recording_url(self):
        event = self.decoder(self.request("recording", {
            **self.base(), "ConferenceSid": CONFERENCE,
            "RecordingStatus": "completed",
            "RecordingUrl": "https://api.twilio.test/private-recording",
        }))
        self.assertEqual(event.event_type, EventType.RECORDING_READY)
        self.assertNotIn("private-recording", repr(event))

    def test_non_affirmative_gather_digit_is_a_durable_decline_event(self):
        event = self.decoder(self.request("consent", {**self.base(), "Digits": "9"}))
        self.assertEqual(event.event_type, EventType.PARTICIPANT_DECLINED)
        self.assertEqual(event.participant_ref, "participant-internal-1")

    def test_empty_gather_result_is_a_decline_not_an_implicit_consent(self):
        event = self.decoder(self.request("consent", self.base()))
        self.assertEqual(event.event_type, EventType.PARTICIPANT_DECLINED)

    def test_absent_recording_callback_fails_closed(self):
        event = self.decoder(self.request("recording", {
            **self.base(), "ConferenceSid": CONFERENCE, "RecordingStatus": "absent",
        }))
        self.assertEqual(event.event_type, EventType.RECORDING_FAILED)

    def test_recording_start_is_normalized_before_completed_callback(self):
        event = self.decoder(self.request("recording", {
            **self.base(), "ConferenceSid": CONFERENCE, "RecordingStatus": "in-progress",
        }))
        self.assertEqual(event.event_type, EventType.RECORDING_STARTED)

    def test_completed_call_status_is_not_mistaken_for_consent(self):
        event = self.decoder(self.request("call-status", {
            **self.base(), "CallStatus": "completed",
        }))
        self.assertEqual(event.event_type, EventType.PARTICIPANT_DECLINED)

    def test_no_answer_call_status_fails_the_session_participant_closed(self):
        event = self.decoder(self.request("call-status", {
            **self.base(), "CallStatus": "no-answer",
        }))
        self.assertEqual(event.event_type, EventType.PARTICIPANT_DECLINED)
        self.assertEqual(event.participant_ref, "participant-internal-1")
    def test_wrong_account_is_rejected_before_resource_resolution(self):
        fields = {**self.base(), "AccountSid": "AC" + "d" * 32, "Digits": "1"}
        with self.assertRaises(TwilioEventDecodeError):
            self.decoder(self.request("consent", fields))
        self.assertEqual(self.resolutions, [])

    def test_duplicate_security_sensitive_field_is_rejected(self):
        request = self.request("consent", {**self.base(), "Digits": "1"})
        request = SignedWebhookRequest(
            method=request.method, public_url=request.public_url,
            content_type=request.content_type, raw_body=request.raw_body,
            headers=request.headers,
            form_parameters={**request.form_parameters, "AccountSid": (ACCOUNT, ACCOUNT)},
        )
        with self.assertRaises(TwilioEventDecodeError):
            self.decoder(request)

    def test_idempotency_header_produces_stable_event_identity(self):
        headers = {"i-twilio-idempotency-token": "twilio-delivery-token"}
        request = self.request("consent", {**self.base(), "Digits": "1"}, headers=headers)
        first = self.decoder(request)
        second = self.decoder(request)
        self.assertEqual(first.event_id, second.event_id)
        self.assertTrue(first.event_id.startswith("twilio_"))

    def test_raw_payload_digest_is_sha256(self):
        request = self.request("consent", {**self.base(), "Digits": "1"})
        event = self.decoder(request)
        self.assertEqual(event.payload_digest, hashlib.sha256(request.raw_body).hexdigest())


if __name__ == "__main__":
    unittest.main()
