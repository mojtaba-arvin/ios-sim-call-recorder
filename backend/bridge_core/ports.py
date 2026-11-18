"""Production infrastructure boundaries; no provider SDK is selected."""
from __future__ import annotations
from collections.abc import Callable, Mapping
from typing import Protocol
from .domain import BridgeSession

class WebhookSignatureVerifier(Protocol):
    """Verify exact, unmodified request bytes using provider-specific rules."""
    def verify(self, raw_body: bytes, headers: Mapping[str, str]) -> bool: ...

class BridgeRepository(Protocol):
    """Atomically deduplicate an event and persist its session mutation.

    Production implementations MUST use a database transaction and unique
    (provider, event_id) constraint. If apply raises, neither write is committed.
    """
    def apply_event_once(self, provider: str, event_id: str, session_id: str,
                         apply: Callable[[BridgeSession], BridgeSession]) -> bool: ...
    def get_session(self, session_id: str) -> BridgeSession | None: ...

class BridgeProvider(Protocol):
    """Server-side provider operations. Credentials never leave the backend."""
    def create_bridge(self, *, session_id: str, idempotency_key: str) -> str: ...
    def start_recording(self, *, provider_session_id: str) -> None: ...
    def stop_recording(self, *, provider_session_id: str) -> None: ...
    def close_bridge(self, *, provider_session_id: str) -> None: ...
