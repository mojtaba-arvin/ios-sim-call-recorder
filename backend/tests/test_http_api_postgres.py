from __future__ import annotations
import hashlib, json, os, unittest
try:
    import psycopg
except ImportError:
    psycopg=None
from bridge_core.http_api import BearerTokenAuthenticator, BridgeSessionsASGI
from bridge_core.persistence import PostgresBridgeRepository

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

if __name__=='__main__': unittest.main()
