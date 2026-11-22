# Authenticated tenant-scoped ASGI endpoints for bridge sessions.
from __future__ import annotations

from bridge_core.address_vault import ParticipantAddressInUseError
import hashlib, hmac, json, re
from typing import Any
from uuid import uuid4
from .domain import BridgeSession, InvalidTransition, SessionState
from .persistence import RateLimitStoreUnavailable, SessionIdempotencyConflict

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
    MAX_PARTICIPANTS = 2
    DEFAULT_RATE_LIMITS = {"read": (120, 2.0), "write": (30, 0.5)}

    def __init__(self, *, repository, authenticator, initial_commands=None, address_vault=None, media_service=None, rate_limits=None):
        self.repository, self.authenticator = repository, authenticator
        self.initial_commands = initial_commands
        self.address_vault = address_vault
        self.media_service = media_service
        self.rate_limits = dict(rate_limits or self.DEFAULT_RATE_LIMITS)
        if set(self.rate_limits) != {"read", "write"} or any(
            not isinstance(capacity, int) or capacity < 1 or refill <= 0
            for capacity, refill in self.rate_limits.values()
        ):
            raise ValueError("rate limits must define positive read/write capacities and refill rates")

    async def __call__(self, scope, receive, send):
        if scope.get('type') != 'http':
            await self.respond(send, 404, {'error':'not_found'}); return
        method = scope.get('method', 'GET').upper()
        path = scope.get('path', '')
        if path == '/health/live':
            if method != 'GET':
                await self.respond(send, 405, {'error': 'method_not_allowed'})
            else:
                await self.respond(send, 200, {'status': 'ok'})
            return
        if path == '/health/ready':
            if method != 'GET':
                await self.respond(send, 405, {'error': 'method_not_allowed'})
            else:
                try:
                    self.repository.ping()
                    await self.respond(send, 200, {'status': 'ready'})
                except Exception:
                    await self.respond(send, 503, {'status': 'not_ready'})
            return
        raw_headers = scope.get('headers', [])
        headers = {k.decode('latin-1').lower():v.decode('latin-1') for k,v in raw_headers}
        idempotency_values = [v.decode('latin-1') for k, v in raw_headers if k.lower() == b'idempotency-key']
        tenant = self.authenticator.tenant_for(headers.get('authorization'))
        if tenant is None:
            await self.respond(send, 401, {'error':'unauthorized'}); return
        method, path = scope.get('method','GET').upper(), scope.get('path','')
        parts = [p for p in path.split('/') if p]
        bucket = "write" if method in {"POST", "PUT", "PATCH", "DELETE"} else "read"
        capacity, refill_per_second = self.rate_limits[bucket]
        try:
            allowed, retry_after = self.repository.consume_tenant_rate_limit(
                tenant_id=tenant, bucket=bucket, capacity=capacity,
                refill_per_second=refill_per_second,
            )
        except RateLimitStoreUnavailable:
            await self.respond(send, 503, {"error": "rate_limit_unavailable"}); return
        except Exception:
            await self.respond(send, 503, {"error": "rate_limit_unavailable"}); return
        if not allowed:
            await self.respond(
                send, 429, {"error": "rate_limit_exceeded"},
                extra_headers=[(b"retry-after", str(max(1, retry_after)).encode("ascii"))],
            )
            return
        try:
            if len(parts) == 4 and parts[:2] == ['v1', 'participants'] and parts[3] == 'address':
                participant_ref = parts[2]
                if (not participant_ref or len(participant_ref) > 128
                        or participant_ref != participant_ref.strip()
                        or any(character.isspace() for character in participant_ref)
                        or '/' in participant_ref):
                    await self.respond(send, 400, {'error': 'invalid_request'}); return
                if self.address_vault is None:
                    await self.respond(send, 404, {'error': 'not_found'}); return
                if method == 'PUT':
                    payload = await self.read_json(receive)
                    if set(payload) != {'phone_number'} or not isinstance(payload['phone_number'], str):
                        await self.respond(send, 400, {'error': 'invalid_request'}); return
                    try:
                        self.address_vault.store(
                            tenant_id=tenant, participant_ref=participant_ref,
                            address=payload['phone_number'],
                        )
                    except ParticipantAddressInUseError:
                        await self.respond(send, 409, {'error': 'address_in_use'}); return
                    await self.respond(send, 200, {'status': 'stored'}); return
                if method == 'DELETE':
                    try:
                        self.address_vault.delete(tenant_id=tenant, participant_ref=participant_ref)
                    except ParticipantAddressInUseError:
                        await self.respond(send, 409, {'error': 'address_in_use'}); return
                    await self.respond(send, 200, {'status': 'deleted'}); return
                await self.respond(send, 405, {'error': 'method_not_allowed'}); return
            if method == 'POST' and parts == ['v1','bridge-sessions']:
                if len(idempotency_values) != 1:
                    await self.respond(send,400,{'error':'idempotency_key_required'}); return
                idempotency_key = idempotency_values[0]
                if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}', idempotency_key) is None:
                    await self.respond(send,400,{'error':'invalid_idempotency_key'}); return
                payload = await self.read_json(receive)
                refs = payload.get('participant_refs')
                if set(payload) != {'participant_refs'} or not isinstance(refs,list) or not 2 <= len(refs) <= self.MAX_PARTICIPANTS or any(not isinstance(x,str) for x in refs) or len(set(refs)) != len(refs):
                    await self.respond(send,400,{'error':'invalid_request'}); return
                canonical_request = json.dumps(
                    {'participant_refs': sorted(refs)}, separators=(',', ':'), sort_keys=True,
                ).encode('utf-8')
                request_digest = hashlib.sha256(canonical_request).hexdigest()
                state = SessionState.AWAITING_USER_ACTION if self.initial_commands else SessionState.CREATED
                session = BridgeSession(str(uuid4()),len(refs),frozenset(refs),state=state)
                commands = tuple(self.initial_commands(session)) if self.initial_commands else ()
                try:
                    persisted, replayed = self.repository.create_session_idempotently(
                        session, tenant_id=tenant, idempotency_key=idempotency_key,
                        request_digest=request_digest, commands=commands,
                    )
                except SessionIdempotencyConflict:
                    await self.respond(send,409,{'error':'idempotency_key_reused'}); return
                await self.respond(send,200 if replayed else 201,self.serialize(persisted)); return
            if len(parts) == 4 and parts[:2] == ['v1','bridge-sessions'] and parts[3] == 'media' and method == 'GET':
                if self.media_service is None:
                    await self.respond(send, 404, {'error': 'not_found'}); return
                result = self.media_service.create_download(tenant_id=tenant, session_id=parts[2])
                if result is None:
                    await self.respond(send, 404, {'error': 'not_found'}); return
                await self.respond(send, 200, result); return
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
    async def respond(send,status,payload,extra_headers=()):
        body=json.dumps(payload,separators=(',',':'),sort_keys=True).encode('utf-8')
        response_headers=[(b'content-type',b'application/json; charset=utf-8'),(b'cache-control',b'no-store'),(b'content-length',str(len(body)).encode('ascii'))]
        response_headers.extend(extra_headers)
        await send({'type':'http.response.start','status':status,'headers':response_headers})
        await send({'type':'http.response.body','body':body})
