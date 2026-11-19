"""Twilio webhook signature verification using the official helper library."""
from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

from twilio.request_validator import RequestValidator

from bridge_core.ports import SignedWebhookRequest


class _FormParameterView(dict):
    """Adapt plain mappings to the multi-value interface expected by Twilio SDK."""

    def getall(self, key):
        value = self[key]
        return [value] if isinstance(value, str) else list(value)


class TwilioWebhookSignatureVerifier:
    """Validates Twilio POST callbacks using its documented SDK semantics.

    Form callbacks are validated with all syntactically parsed form fields.
    JSON callbacks are validated against the original UTF-8 body and the
    bodySHA256 query parameter. Business event decoding must happen afterwards.
    """

    _FORM = "application/x-www-form-urlencoded"
    _JSON = "application/json"

    def __init__(self, auth_token: str) -> None:
        if not auth_token or not auth_token.strip():
            raise ValueError("Twilio Auth Token must be supplied from secret storage")
        self._validator = RequestValidator(auth_token)

    def verify(self, request: SignedWebhookRequest) -> bool:
        if request.method.upper() != "POST":
            return False

        signature = self._header(request.headers, "x-twilio-signature")
        if not signature:
            return False

        media_type = request.content_type.split(";", 1)[0].strip().lower()
        if media_type == self._FORM:
            if request.form_parameters is None:
                return False
            params: object = _FormParameterView(request.form_parameters)
        elif media_type == self._JSON:
            query = parse_qs(urlsplit(request.public_url).query, keep_blank_values=True)
            body_hash = query.get("bodySHA256", [])
            if len(body_hash) != 1 or not body_hash[0]:
                return False
            try:
                params = request.raw_body.decode("utf-8")
            except UnicodeDecodeError:
                return False
        else:
            return False

        # The SDK owns Twilio's URL/parameter/body-hash/HMAC details. Malformed
        # transport data fails closed and never reaches business decoding.
        try:
            return self._validator.validate(request.public_url, params, signature)
        except (TypeError, ValueError, UnicodeError, KeyError):
            return False

    @staticmethod
    def _header(headers, expected_name: str) -> str | None:
        for name, value in headers.items():
            if name.lower() == expected_name:
                return value
        return None
