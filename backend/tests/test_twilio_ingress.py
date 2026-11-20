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
        def decode(request):
            self.seen.append(request)
            return self.event
        processor = WebhookProcessor(verifier=Verifier(),repository=self.repo)
        self.app = TwilioWebhookASGI(processor=processor,decode_verified_request=decode,canonical_public_origin='https://hooks.example.test')

    async def request(self, signature='valid', body=b'CallSid=CA123&Status=ringing&Status=answered', query=b'tenant=acct&x=1'):
        incoming=[{'type':'http.request','body':body,'more_body':False}]
        sent=[]
        async def receive(): return incoming.pop(0)
        async def send(message): sent.append(message)
        scope={'type':'http','method':'POST','path':'/twilio/events','raw_path':b'/twilio/events','query_string':query,'headers':[(b'content-type',b'application/x-www-form-urlencoded'),(b'x-test-signature',signature.encode())]}
        await self.app(scope,receive,send)
        return next(m['status'] for m in sent if m['type']=='http.response.start')

    async def test_signature_is_verified_before_decoder_and_exact_request_is_passed(self):
        status=await self.request()
        self.assertEqual(status,204)
        self.assertEqual(len(self.seen),1)
        request=self.seen[0]
        self.assertEqual(request.public_url,'https://hooks.example.test/twilio/events?tenant=acct&x=1')
        self.assertEqual(request.form_parameters['Status'],('ringing','answered'))
        self.assertEqual(request.raw_body,b'CallSid=CA123&Status=ringing&Status=answered')

    async def test_invalid_signature_never_calls_decoder(self):
        status=await self.request(signature='invalid')
        self.assertEqual(status,403)
        self.assertEqual(self.seen,[])

    async def test_non_https_origin_is_rejected(self):
        with self.assertRaises(ValueError):
            TwilioWebhookASGI(processor=None,decode_verified_request=lambda _:None,canonical_public_origin='http://bad.example')

if __name__=='__main__': unittest.main()
