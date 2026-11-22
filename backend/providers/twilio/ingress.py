# ASGI ingress for provider-signed webhooks; business decoding is injected after verification.
from __future__ import annotations

from typing import Any, Callable
from urllib.parse import parse_qs, urlsplit

from bridge_core.ports import SignedWebhookRequest
from bridge_core.webhooks import InvalidWebhookSignature, UnknownSession


class WebhookRateLimitExceeded(RuntimeError):
    def __init__(self, retry_after: int):
        super().__init__("provider webhook rate limit exceeded")
        self.retry_after = max(1, int(retry_after))


class WebhookRateLimitUnavailable(RuntimeError):
    pass


class TwilioWebhookASGI:
    MAX_BODY_BYTES = 256 * 1024

    def __init__(
        self, *, processor, decode_verified_request, canonical_public_origin,
        rate_limit: Callable[[], tuple[bool, int]], after_process=None,
    ):
        parts = urlsplit(canonical_public_origin)
        if (
            parts.scheme != "https" or not parts.netloc or parts.username or parts.password
            or parts.path not in ("", "/") or parts.query or parts.fragment
        ):
            raise ValueError("canonical public origin must be an HTTPS origin without path/query")
        if not callable(rate_limit):
            raise ValueError("a verified-provider rate-limit callback is required")
        self.processor = processor
        self.decode = decode_verified_request
        self.rate_limit = rate_limit
        self.after_process = after_process
        self.origin = f"https://{parts.netloc}"

    async def __call__(self, scope: dict[str, Any], receive, send):
        if scope.get("type") != "http" or scope.get("method", "").upper() != "POST":
            await self.respond(send, 405)
            return
        body = bytearray()
        while True:
            message = await receive()
            if message.get("type") == "http.disconnect":
                await self.respond(send, 400)
                return
            body.extend(message.get("body", b""))
            if len(body) > self.MAX_BODY_BYTES:
                await self.respond(send, 413)
                return
            if not message.get("more_body", False):
                break

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        content_type = headers.get("content-type", "")
        raw_path = scope.get("raw_path") or scope.get("path", "/").encode("utf-8")
        query = scope.get("query_string", b"")
        public_url = self.origin + raw_path.decode("latin-1")
        if query:
            public_url += "?" + query.decode("latin-1")

        form = None
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type == "application/x-www-form-urlencoded":
            try:
                parsed = parse_qs(
                    body.decode("utf-8"), keep_blank_values=True,
                    strict_parsing=True, max_num_fields=256,
                )
                form = {key: tuple(values) for key, values in parsed.items()}
            except (UnicodeDecodeError, ValueError):
                await self.respond(send, 400)
                return
        try:
            request = SignedWebhookRequest(
                method="POST", public_url=public_url, content_type=content_type,
                raw_body=bytes(body), headers=headers, form_parameters=form,
            )
        except ValueError:
            await self.respond(send, 400)
            return

        def admit_verified_request(_request: SignedWebhookRequest) -> None:
            try:
                allowed, retry_after = self.rate_limit()
            except Exception as exc:
                raise WebhookRateLimitUnavailable("provider webhook admission store unavailable") from exc
            if not allowed:
                raise WebhookRateLimitExceeded(retry_after)

        try:
            accepted = self.processor.process(
                request=request, decode=self.decode, before_decode=admit_verified_request,
            )
            if self.after_process is not None:
                self.after_process(request, accepted)
        except InvalidWebhookSignature:
            await self.respond(send, 403)
            return
        except WebhookRateLimitExceeded as limited:
            await self.respond(
                send, 429, extra_headers=[(b"retry-after", str(limited.retry_after).encode("ascii"))],
            )
            return
        except WebhookRateLimitUnavailable:
            await self.respond(send, 503)
            return
        except UnknownSession:
            await self.respond(send, 404)
            return
        except (ValueError, KeyError):
            await self.respond(send, 400)
            return
        except Exception:
            await self.respond(send, 500)
            return

        if urlsplit(public_url).path.rstrip("/").endswith("/consent"):
            body = b'<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>'
            await self.respond(send, 200, body=body, content_type=b"application/xml; charset=utf-8")
            return
        await self.respond(send, 204)

    @staticmethod
    async def respond(send, status, *, body=b"", content_type=None, extra_headers=()):
        headers = [(b"cache-control", b"no-store"), (b"content-length", str(len(body)).encode("ascii"))]
        if content_type:
            headers.append((b"content-type", content_type))
        headers.extend(extra_headers)
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body})
