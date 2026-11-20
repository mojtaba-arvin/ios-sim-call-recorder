"""TwiML helpers for the explicit, pre-bridge consent gate."""
from __future__ import annotations

from html import escape


def build_consent_gather_twiml(*, disclosure: str, action_url: str, language: str = "en-US") -> str:
    """Prompt one participant and collect a single affirmative DTMF digit.

    The disclosure is supplied by deployment configuration and must be the
    exact text approved for the target jurisdiction. This helper does not make
    an unreviewed disclosure legally sufficient.
    """
    if not isinstance(disclosure, str) or not disclosure.strip() or len(disclosure) > 4000:
        raise ValueError("a bounded, non-empty consent disclosure is required")
    if not action_url.startswith("https://"):
        raise ValueError("consent action URL must use HTTPS")
    if not language or len(language) > 32:
        raise ValueError("invalid consent language")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Response><Gather input="dtmf" numDigits="1" timeout="10" '
        'actionOnEmptyResult="true" method="POST" action="'
        + escape(action_url, quote=True)
        + '"><Say language="'
        + escape(language, quote=True)
        + '">'
        + escape(disclosure)
        + ' Press 1 to agree to recording. Any other key declines.</Say></Gather>'
        '<Hangup/></Response>'
    )


def build_consent_result_twiml() -> str:
    """End the consent call after its signed Gather callback is processed."""
    return '<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>'
