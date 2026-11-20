from __future__ import annotations
import hashlib, json, os, unittest
try:
    import psycopg
except ImportError:
    psycopg=None
from bridge_core.http_api import BearerTokenAuthenticator, BridgeSessionsASGI
from bridge_core.persistence import PostgresBridgeRepository
from bridge_core.domain import BridgeSession, SessionState
from providers.twilio.factory import TwilioConsentCommandFactory

DATABASE_URL=os.environ.get('TEST_DATABASE_URL')
SKIP=psycopg is None or not DATABASE_URL

@unittest.skipIf(SKIP,'TEST_DATABASE_URL and psycopg are required')
class PostgresHTTPAPITests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.connect=staticmethod(lambda:psycopg.connect(DATABASE_URL))
        from pathlib import Path
        with cls.connect() as conn:
            for migration in sorted((Path(__file__).parents[1]/'migrations').glob('*.sql')):
                conn.execute(migration.read_text(encoding='utf-8'))

    async def asyncSetUp(self):
        with self.connect() as conn:
            conn.execute('TRUNCATE outbox_commands, provider_event_receipts, bridge_sessions CASCADE')
        self.token='integration-token-' + 'x'*40
        self.repo=PostgresBridgeRepository(self.connect)
        self.app=BridgeSessionsASGI(repository=self.repo,authenticator=BearerTokenAuthenticator({hashlib.sha256(self.token.encode()).hexdigest():'tenant-integration'}))

    async def request(self,method,path,body=None):
        raw=json.dumps(body).encode() if body is not None else b''
        incoming=[{'type':'http.request','body':raw,'more_body':False}]
        outgoing=[]
        async def receive(): return incoming.pop(0)
        async def send(message): outgoing.append(message)
        await self.app({'type':'http','method':method,'path':path,'headers':[(b'authorization',f'Bearer {self.token}'.encode())]},receive,send)
        start=next(item for item in outgoing if item['type']=='http.response.start')
        payload=next(item for item in outgoing if item['type']=='http.response.body')['body']
        return start['status'],json.loads(payload) if payload else None

    async def test_authenticated_http_create_read_cancel_persists_in_postgres(self):
        status,created=await self.request('POST','/v1/bridge-sessions',{'participant_refs':['participant-a','participant-b']})
        self.assertEqual(status,201)
        session_id=created['session_id']
        self.assertEqual(self.repo.get_session(session_id,tenant_id='tenant-integration').state.value,'created')
        status,loaded=await self.request('GET',f'/v1/bridge-sessions/{session_id}')
        self.assertEqual(status,200)
        self.assertEqual(loaded['session_id'],session_id)
        status,cancelled=await self.request('POST',f'/v1/bridge-sessions/{session_id}/cancel')
        self.assertEqual(status,200)
        self.assertEqual(cancelled['state'],'cancelled')
        self.assertEqual(self.repo.get_session(session_id,tenant_id='tenant-integration').state.value,'cancelled')

    async def test_cancel_during_consent_closes_pending_outbox_and_queues_call_cancellation(self):
        session = BridgeSession(
            "session-consent-cancel",
            2,
            frozenset({"participant-a", "participant-b"}),
            state=SessionState.AWAITING_USER_ACTION,
        )
        commands = TwilioConsentCommandFactory(provider_account_id="twilio-main")(session)
        self.repo.create_session(session, tenant_id="tenant-integration", commands=commands)
        cancelled = self.repo.cancel_session(
            session.session_id, tenant_id="tenant-integration",
        )
        self.assertEqual(cancelled.state, SessionState.CANCELLED)
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT command_type, status FROM outbox_commands WHERE session_id=%s",
                (session.session_id,),
            ).fetchall()
        self.assertEqual(sum(1 for kind, status in rows if kind == "consent.request" and status == "dead"), 2)
        self.assertEqual(sum(1 for kind, status in rows if kind == "consent.cancel" and status == "pending"), 2)

if __name__=='__main__': unittest.main()
