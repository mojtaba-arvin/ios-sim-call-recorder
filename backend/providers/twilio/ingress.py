# ASGI ingress for provider-signed webhooks; business decoding is injected after verification.
from __future__ import annotations
from urllib.parse import parse_qs, urlsplit
from typing import Any
from bridge_core.ports import SignedWebhookRequest
from bridge_core.webhooks import InvalidWebhookSignature, UnknownSession

class TwilioWebhookASGI:
    MAX_BODY_BYTES = 256 * 1024
    def __init__(self, *, processor, decode_verified_request, canonical_public_origin):
        parts = urlsplit(canonical_public_origin)
        if parts.scheme != 'https' or not parts.netloc or parts.username or parts.password or parts.path not in ('','/') or parts.query or parts.fragment:
            raise ValueError('canonical public origin must be an HTTPS origin without path/query')
        self.processor = processor
        self.decode = decode_verified_request
        self.origin = f'https://{parts.netloc}'

    async def __call__(self, scope: dict[str, Any], receive, send):
        if scope.get('type') != 'http' or scope.get('method','').upper() != 'POST':
            await self.respond(send,405); return
        body = bytearray()
        while True:
            message = await receive()
            if message.get('type') == 'http.disconnect':
                await self.respond(send,400); return
            body.extend(message.get('body',b''))
            if len(body) > self.MAX_BODY_BYTES:
                await self.respond(send,413); return
            if not message.get('more_body',False): break
        headers = {k.decode('latin-1').lower():v.decode('latin-1') for k,v in scope.get('headers',[])}
        content_type = headers.get('content-type','')
        raw_path = scope.get('raw_path') or scope.get('path','/').encode('utf-8')
        query = scope.get('query_string',b'')
        public_url = self.origin + raw_path.decode('latin-1')
        if query: public_url += '?' + query.decode('latin-1')
        form = None
        media_type = content_type.split(';',1)[0].strip().lower()
        if media_type == 'application/x-www-form-urlencoded':
            try:
                parsed = parse_qs(body.decode('utf-8'), keep_blank_values=True, strict_parsing=True, max_num_fields=256)
                form = {key: tuple(values) for key,values in parsed.items()}
            except (UnicodeDecodeError, ValueError):
                await self.respond(send,400); return
        try:
            request = SignedWebhookRequest(
                method='POST', public_url=public_url, content_type=content_type,
                raw_body=bytes(body), headers=headers, form_parameters=form,
            )
        except ValueError:
            await self.respond(send,400); return
        try:
            self.processor.process(request=request, decode=self.decode)
        except InvalidWebhookSignature:
            await self.respond(send,403); return
        except UnknownSession:
            await self.respond(send,404); return
        except (ValueError, KeyError):
            await self.respond(send,400); return
        except Exception:
            await self.respond(send,500); return
        await self.respond(send,204)

    @staticmethod
    async def respond(send, status):
        await send({'type':'http.response.start','status':status,'headers':[(b'cache-control',b'no-store'),(b'content-length',b'0')]})
        await send({'type':'http.response.body','body':b''})
