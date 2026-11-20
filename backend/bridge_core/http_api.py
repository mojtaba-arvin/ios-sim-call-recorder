# Authenticated tenant-scoped ASGI endpoints for bridge sessions.
from __future__ import annotations
import hashlib, hmac, json
from typing import Any
from uuid import uuid4
from .domain import BridgeSession, InvalidTransition, SessionState

class BearerTokenAuthenticator:
    def __init__(self, token_hashes):
        self._tokens = {}
        for digest, tenant in token_hashes.items():
            if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest) or not tenant or not tenant.strip():
                raise ValueError('invalid API token hash or tenant identifier')
            self._tokens[digest] = tenant
        if not self._tokens:
            raise ValueError('at least one API token hash is required')

    def tenant_for(self, authorization):
        if not authorization or not authorization.startswith('Bearer '): return None
        token = authorization[7:]
        if len(token) < 32 or token.strip() != token: return None
        digest = hashlib.sha256(token.encode('utf-8')).hexdigest()
        result = None
        for configured, tenant in self._tokens.items():
            if hmac.compare_digest(digest, configured): result = tenant
        return result

class BridgeSessionsASGI:
    MAX_BODY_BYTES = 16384
    MAX_PARTICIPANTS = 10
    def __init__(self, *, repository, authenticator):
        self.repository, self.authenticator = repository, authenticator

    async def __call__(self, scope, receive, send):
        if scope.get('type') != 'http':
            await self.respond(send, 404, {'error':'not_found'}); return
        headers = {k.decode('latin-1').lower():v.decode('latin-1') for k,v in scope.get('headers',[])}
        tenant = self.authenticator.tenant_for(headers.get('authorization'))
        if tenant is None:
            await self.respond(send, 401, {'error':'unauthorized'}); return
        method, path = scope.get('method','GET').upper(), scope.get('path','')
        parts = [p for p in path.split('/') if p]
        try:
            if method == 'POST' and parts == ['v1','bridge-sessions']:
                payload = await self.read_json(receive)
                refs = payload.get('participant_refs')
                if set(payload) != {'participant_refs'} or not isinstance(refs,list) or not 2 <= len(refs) <= self.MAX_PARTICIPANTS or any(not isinstance(x,str) for x in refs) or len(set(refs)) != len(refs):
                    await self.respond(send,400,{'error':'invalid_request'}); return
                session = BridgeSession(str(uuid4()),len(refs),frozenset(refs),state=SessionState.CREATED)
                self.repository.create_session(session,tenant_id=tenant)
                await self.respond(send,201,self.serialize(session)); return
            if len(parts) == 3 and parts[:2] == ['v1','bridge-sessions'] and method == 'GET':
                session = self.repository.get_session(parts[2],tenant_id=tenant)
                if session is None: await self.respond(send,404,{'error':'not_found'})
                else: await self.respond(send,200,self.serialize(session))
                return
            if len(parts) == 4 and parts[:2] == ['v1','bridge-sessions'] and parts[3] == 'cancel' and method == 'POST':
                session = self.repository.cancel_session(parts[2],tenant_id=tenant)
                await self.respond(send,200,self.serialize(session)); return
            await self.respond(send,404,{'error':'not_found'})
        except InvalidTransition:
            await self.respond(send,409,{'error':'session_cannot_be_cancelled'})
        except KeyError:
            await self.respond(send,404,{'error':'not_found'})
        except ValueError:
            await self.respond(send,400,{'error':'invalid_request'})
        except Exception:
            await self.respond(send,500,{'error':'internal_error'})

    async def read_json(self, receive):
        body=bytearray()
        while True:
            message=await receive()
            if message.get('type') == 'http.disconnect': raise ValueError('disconnect')
            body.extend(message.get('body',b''))
            if len(body)>self.MAX_BODY_BYTES: raise ValueError('body too large')
            if not message.get('more_body',False): break
        try: value=json.loads(body)
        except (UnicodeDecodeError,json.JSONDecodeError) as exc: raise ValueError('invalid JSON') from exc
        if not isinstance(value,dict): raise ValueError('JSON object required')
        return value

    @staticmethod
    def serialize(session):
        return {'session_id':session.session_id,'state':session.state.value,'expected_participants':session.expected_participants,'joined_participants':len(session.joined_participants),'consented_participants':len(session.consented_participants),'failure_code':session.failure_code,'updated_at':session.updated_at.isoformat() if session.updated_at else None}

    @staticmethod
    async def respond(send,status,payload):
        body=json.dumps(payload,separators=(',',':'),sort_keys=True).encode('utf-8')
        await send({'type':'http.response.start','status':status,'headers':[(b'content-type',b'application/json; charset=utf-8'),(b'cache-control',b'no-store'),(b'content-length',str(len(body)).encode('ascii'))]})
        await send({'type':'http.response.body','body':body})
