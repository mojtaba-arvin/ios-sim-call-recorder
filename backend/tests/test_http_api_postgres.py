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
from bridge_core.media_access import PostgresMediaDownloadService
from bridge_core.address_vault import EncryptedParticipantAddressCodec, PostgresParticipantAddressResolver, ParticipantAddressInUseError

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
            conn.execute('TRUNCATE tenant_api_rate_limits, outbox_commands, provider_event_receipts, bridge_sessions CASCADE')
        self.token='integration-token-' + 'x'*40
        self.repo=PostgresBridgeRepository(self.connect)
        self.app=BridgeSessionsASGI(repository=self.repo,authenticator=BearerTokenAuthenticator({hashlib.sha256(self.token.encode()).hexdigest():'tenant-integration'}))

    async def request(self,method,path,body=None,idempotency_key='pg-session-key-001'):
        raw=json.dumps(body).encode() if body is not None else b''
        incoming=[{'type':'http.request','body':raw,'more_body':False}]
        outgoing=[]
        async def receive(): return incoming.pop(0)
        async def send(message): outgoing.append(message)
        headers=[(b'authorization',f'Bearer {self.token}'.encode())]
        if idempotency_key is not None:
            headers.append((b'idempotency-key',idempotency_key.encode()))
        await self.app({'type':'http','method':method,'path':path,'headers':headers},receive,send)
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

    async def test_http_session_create_replay_and_payload_conflict_are_durable(self):
        body = {'participant_refs':['participant-a','participant-b']}
        status, first = await self.request('POST','/v1/bridge-sessions',body,'durable-retry-key')
        self.assertEqual(status,201)
        replay_status, replay = await self.request('POST','/v1/bridge-sessions',body,'durable-retry-key')
        self.assertEqual(replay_status,200)
        self.assertEqual(replay['session_id'],first['session_id'])
        conflict_status, conflict = await self.request(
            'POST','/v1/bridge-sessions',
            {'participant_refs':['participant-c','participant-d']},'durable-retry-key',
        )
        self.assertEqual(conflict_status,409)
        self.assertEqual(conflict,{'error':'idempotency_key_reused'})
        with self.connect() as conn:
            count=conn.execute(
                "SELECT count(*) FROM bridge_sessions WHERE tenant_id=%s",
                ('tenant-integration',),
            ).fetchone()[0]
        self.assertEqual(count,1)

    async def test_tenant_rate_limit_is_atomic_across_concurrent_connections(self):
        from concurrent.futures import ThreadPoolExecutor

        def consume(_):
            return self.repo.consume_tenant_rate_limit(
                tenant_id="tenant-rate-limit",
                bucket="write",
                capacity=5,
                refill_per_second=0.0001,
            )

        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(consume, range(12)))
        self.assertEqual(sum(1 for allowed, _ in results if allowed), 5)
        rejected = [retry for allowed, retry in results if not allowed]
        self.assertEqual(len(rejected), 7)
        self.assertTrue(all(value >= 1 for value in rejected))

        other_tenant = self.repo.consume_tenant_rate_limit(
            tenant_id="tenant-rate-limit-other",
            bucket="write",
            capacity=1,
            refill_per_second=0.0001,
        )
        self.assertEqual(other_tenant, (True, 0))

    async def test_cancel_during_consent_closes_pending_outbox_and_queues_call_cancellation(self):
        session = BridgeSession(
            "session-consent-cancel",
            2,
            frozenset({"participant-a", "participant-b"}),
            state=SessionState.AWAITING_USER_ACTION,
        )
        commands = TwilioConsentCommandFactory(provider_account_id="twilio-main")(session)
        address_vault = PostgresParticipantAddressResolver(
            connect=self.connect,
            codec=EncryptedParticipantAddressCodec(b"\x11" * 32),
        )
        address_vault.store(tenant_id="tenant-integration", participant_ref="participant-a", address="+14155550101")
        address_vault.store(tenant_id="tenant-integration", participant_ref="participant-b", address="+14155550102")
        self.repo.create_session(session, tenant_id="tenant-integration", commands=commands)
        with self.assertRaises(ParticipantAddressInUseError):
            address_vault.store(
                tenant_id="tenant-integration", participant_ref="participant-a",
                address="+14155550199",
            )
        with self.assertRaises(ParticipantAddressInUseError):
            address_vault.delete(tenant_id="tenant-integration", participant_ref="participant-b")
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
        address_vault.store(
            tenant_id="tenant-integration", participant_ref="participant-a",
            address="+14155550199",
        )

    async def test_verified_media_download_is_scoped_and_audited(self):
        session_id = "session-media-audit"
        session = BridgeSession(session_id, 2, frozenset({"a", "b"}))
        self.repo.create_session(session, tenant_id="tenant-media")
        media_id = "00000000-0000-4000-8000-000000000001"
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO media_assets
                (media_id,tenant_id,session_id,provider,provider_account_id,
                 provider_recording_sid,object_key,sha256,byte_count,duration_seconds,
                 sample_rate_hz,channel_count,channel_activity,channel_map,
                 verification_state,retention_expires_at)
                VALUES (%s,%s,%s,'twilio','account-opaque','RE00000000000000000000000000000001',
                        'tenants/x/object.wav',%s,1024,1.0,8000,2,'[0.8,0.9]'::jsonb,
                        '{"channel_1":"a","channel_2":"b"}'::jsonb,'verified',now()+interval '30 days')""",
                (media_id, "tenant-media", session_id, "a" * 64),
            )
        class FakeStore:
            def presigned_download_url(self, **kwargs):
                self.kwargs = kwargs
                return "https://media.example.test/signed"
        store = FakeStore()
        service = PostgresMediaDownloadService(connect=self.connect, object_store=store)
        result = service.create_download(tenant_id="tenant-media", session_id=session_id)
        self.assertEqual(result["download_url"], "https://media.example.test/signed")
        self.assertEqual(result["channel_map"], {"channel_1": "a", "channel_2": "b"})
        with self.connect() as conn:
            audit = conn.execute(
                "SELECT tenant_id, session_id, media_id, action, expires_in_seconds FROM media_access_audit WHERE media_id=%s",
                (media_id,),
            ).fetchone()
        self.assertEqual(audit[:2], ("tenant-media", session_id))
        self.assertEqual(str(audit[2]), media_id)
        self.assertEqual(audit[3:], ("download_url_issued", 120))

if __name__=='__main__': unittest.main()
