from __future__ import annotations
import unittest
from datetime import datetime, timezone
from bridge_core.domain import BridgeSession, EventType, SessionState
from bridge_core.memory import InMemoryBridgeRepository
from bridge_core.webhooks import NormalizedProviderEvent, WebhookProcessor
from bridge_core.ports import SignedWebhookRequest
from providers.twilio.ingress import TwilioWebhookASGI

class Verifier:
    def verify(self, request):
        return request.headers.get('x-test-signature') == 'valid' and bool(request.raw_body)

class TwilioIngressTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.repo = InMemoryBridgeRepository()
        self.repo.add_session(BridgeSession('s-1',2,frozenset({'a','b'}),state=SessionState.AWAITING_USER_ACTION))
        self.now = datetime(2026,11,20,tzinfo=timezone.utc)
        self.event = NormalizedProviderEvent('twilio','evt-1','s-1',EventType.BRIDGE_RINGING,self.now,payload_digest='sha256:x')
        self.seen = []
        self.rate_limit_calls = 0
        self.rate_limit_result = (True, 0)
        self.timeline = []
        def decode(request):
            self.timeline.append("decode")
            self.seen.append(request)
            return self.event
        def rate_limit():
            self.rate_limit_calls += 1
            self.timeline.append("rate_limit")
            return self.rate_limit_result
        processor = WebhookProcessor(verifier=Verifier(),repository=self.repo)
        self.app = TwilioWebhookASGI(
            processor=processor, decode_verified_request=decode,
            canonical_public_origin='https://hooks.example.test', rate_limit=rate_limit,
        )

    async def request(self, signature='valid', body=b'CallSid=CA123&Status=ringing&Status=answered', query=b'tenant=acct&x=1', path='/twilio/events'):
        incoming=[{'type':'http.request','body':body,'more_body':False}]
        sent=[]
        async def receive(): return incoming.pop(0)
        async def send(message): sent.append(message)
        scope={'type':'http','method':'POST','path':path,'raw_path':path.encode(),'query_string':query,'headers':[(b'content-type',b'application/x-www-form-urlencoded'),(b'x-test-signature',signature.encode())]}
        await self.app(scope,receive,send)
        start = next(m for m in sent if m['type']=='http.response.start')
        self.last_headers = dict(start.get('headers', []))
        return start['status']

    async def test_signature_is_verified_before_decoder_and_exact_request_is_passed(self):
        status=await self.request()
        self.assertEqual(status,204)
        self.assertEqual(len(self.seen),1)
        request=self.seen[0]
        self.assertEqual(request.public_url,'https://hooks.example.test/twilio/events?tenant=acct&x=1')
        self.assertEqual(request.form_parameters['Status'],('ringing','answered'))
        self.assertEqual(request.raw_body,b'CallSid=CA123&Status=ringing&Status=answered')
        self.assertEqual(self.timeline, ["rate_limit", "decode"])
        self.assertEqual(self.rate_limit_calls, 1)

    async def test_consent_route_returns_hangup_twiml_to_twilio(self):
        status = await self.request(path="/twilio/consent")
        self.assertEqual(status, 200)
        self.assertEqual(self.seen[-1].public_url, "https://hooks.example.test/twilio/consent?tenant=acct&x=1")

    async def test_invalid_signature_never_calls_decoder(self):
        status=await self.request(signature='invalid')
        self.assertEqual(status,403)
        self.assertEqual(self.seen,[])
        self.assertEqual(self.rate_limit_calls, 0)


    async def test_signed_webhook_rate_limit_returns_retry_after_before_decode(self):
        self.rate_limit_result = (False, 9)
        status = await self.request()
        self.assertEqual(status, 429)
        self.assertEqual(self.last_headers.get(b"retry-after"), b"9")
        self.assertEqual(self.seen, [])
        self.assertEqual(self.rate_limit_calls, 1)

    async def test_rate_limit_store_failure_fails_closed_before_decode(self):
        def unavailable():
            raise RuntimeError("database unavailable")
        self.app.rate_limit = unavailable
        status = await self.request()
        self.assertEqual(status, 503)
        self.assertEqual(self.seen, [])
        self.assertEqual(self.rate_limit_calls, 0)

    async def test_non_https_origin_is_rejected(self):
        with self.assertRaises(ValueError):
            TwilioWebhookASGI(processor=None,decode_verified_request=lambda _:None,canonical_public_origin='http://bad.example',rate_limit=lambda:(True,0))

if __name__=='__main__': unittest.main()
