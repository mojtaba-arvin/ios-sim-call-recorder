from __future__ import annotations

import hashlib
import unittest
from urllib.parse import urlencode

from twilio.request_validator import RequestValidator

from bridge_core.ports import SignedWebhookRequest
from providers.twilio import TwilioWebhookSignatureVerifier


class MultiValueParams(dict):
    def getall(self, key):
        value = self[key]
        return [value] if isinstance(value, str) else list(value)


class TwilioSignatureTests(unittest.TestCase):
    TOKEN = "synthetic-test-auth-token"

    def setUp(self):
        self.validator = RequestValidator(self.TOKEN)
        self.verifier = TwilioWebhookSignatureVerifier(self.TOKEN)

    def request(self, url, *, body, content_type, signature,
                form_parameters=None, method="POST"):
        return SignedWebhookRequest(
            method=method,
            public_url=url,
            content_type=content_type,
            raw_body=body,
            headers={"x-twilio-signature": signature} if signature is not None else {},
            form_parameters=form_parameters,
        )

    def test_valid_form_webhook(self):
        url = "https://hooks.example.test/twilio/voice?tenant=demo"
        params = {"CallSid": "CA00000000000000000000000000000000",
                  "CallStatus": "in-progress", "From": "+15550000001"}
        signature = self.validator.compute_signature(url, params)
        request = self.request(url, body=urlencode(params).encode(),
                               content_type="application/x-www-form-urlencoded; charset=utf-8",
                               signature=signature, form_parameters=params)
        self.assertTrue(self.verifier.verify(request))

    def test_modified_form_parameter_is_rejected(self):
        url = "https://hooks.example.test/twilio/voice"
        signed = {"CallSid": "CA00000000000000000000000000000000", "CallStatus": "ringing"}
        signature = self.validator.compute_signature(url, signed)
        tampered = dict(signed, CallStatus="completed")
        request = self.request(url, body=urlencode(tampered).encode(),
                               content_type="application/x-www-form-urlencoded",
                               signature=signature, form_parameters=tampered)
        self.assertFalse(self.verifier.verify(request))

    def test_form_webhook_preserves_multi_value_parameters(self):
        url = "https://hooks.example.test/twilio/voice"
        params = MultiValueParams({"Tag": ["alpha", "beta"], "CallSid": "CA00000000000000000000000000000000"})
        signature = self.validator.compute_signature(url, params)
        request = self.request(url, body=b"Tag=alpha&Tag=beta",
                               content_type="application/x-www-form-urlencoded",
                               signature=signature,
                               form_parameters={"Tag": ["alpha", "beta"], "CallSid": "CA00000000000000000000000000000000"})
        self.assertTrue(self.verifier.verify(request))

    def test_valid_json_webhook_uses_raw_body_hash(self):
        body = b'{"id":"EV00000000000000000000000000000000","type":"com.twilio.voice.call.answered"}'
        digest = hashlib.sha256(body).hexdigest()
        url = "https://hooks.example.test/twilio/events?" + urlencode({"bodySHA256": digest})
        signature = self.validator.compute_signature(url, {})
        request = self.request(url, body=body, content_type="application/json",
                               signature=signature)
        self.assertTrue(self.verifier.verify(request))

    def test_modified_json_body_is_rejected(self):
        body = b'{"event":"recording.completed"}'
        digest = hashlib.sha256(body).hexdigest()
        url = "https://hooks.example.test/twilio/events?" + urlencode({"bodySHA256": digest})
        signature = self.validator.compute_signature(url, {})
        request = self.request(url, body=b'{"event":"recording.failed"}',
                               content_type="application/json", signature=signature)
        self.assertFalse(self.verifier.verify(request))

    def test_json_without_body_sha256_is_rejected(self):
        url = "https://hooks.example.test/twilio/events"
        signature = self.validator.compute_signature(url, {})
        request = self.request(url, body=b'{"event":"call.ended"}',
                               content_type="application/json", signature=signature)
        self.assertFalse(self.verifier.verify(request))

    def test_wrong_public_url_is_rejected(self):
        signed_url = "https://hooks.example.test/twilio/voice?tenant=one"
        received_url = "https://hooks.example.test/twilio/voice?tenant=two"
        params = {"CallSid": "CA00000000000000000000000000000000"}
        signature = self.validator.compute_signature(signed_url, params)
        request = self.request(received_url, body=b"CallSid=CA00000000000000000000000000000000",
                               content_type="application/x-www-form-urlencoded",
                               signature=signature, form_parameters=params)
        self.assertFalse(self.verifier.verify(request))

    def test_missing_signature_is_rejected(self):
        request = self.request("https://hooks.example.test/twilio/voice", body=b"",
                               content_type="application/x-www-form-urlencoded",
                               signature=None, form_parameters={})
        self.assertFalse(self.verifier.verify(request))

    def test_unsupported_content_type_is_rejected(self):
        request = self.request("https://hooks.example.test/twilio/voice", body=b"hello",
                               content_type="text/plain", signature="not-a-signature")
        self.assertFalse(self.verifier.verify(request))

    def test_form_request_requires_parsed_parameters(self):
        request = self.request("https://hooks.example.test/twilio/voice", body=b"CallSid=CA123",
                               content_type="application/x-www-form-urlencoded",
                               signature="not-a-signature")
        self.assertFalse(self.verifier.verify(request))

    def test_get_webhook_is_not_accepted_by_this_adapter(self):
        request = self.request("https://hooks.example.test/twilio/voice", body=b"",
                               content_type="application/x-www-form-urlencoded",
                               signature="not-a-signature", form_parameters={}, method="GET")
        self.assertFalse(self.verifier.verify(request))

    def test_non_utf8_json_body_is_rejected(self):
        body = bytes([255])
        digest = hashlib.sha256(body).hexdigest()
        url = "https://hooks.example.test/twilio/events?" + urlencode({"bodySHA256": digest})
        signature = self.validator.compute_signature(url, {})
        request = self.request(url, body=body, content_type="application/json", signature=signature)
        self.assertFalse(self.verifier.verify(request))

    def test_empty_auth_token_is_rejected(self):
        with self.assertRaises(ValueError):
            TwilioWebhookSignatureVerifier(" ")


if __name__ == "__main__":
    unittest.main()
