"""Production infrastructure boundaries; no provider SDK is selected."""
from __future__ import annotations
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol
from .application import EventApplication
from .domain import BridgeSession

@dataclass(frozen=True, slots=True)
class SignedWebhookRequest:
    """Transport facts required by provider-native signature validators.

    public_url must be reconstructed from trusted deployment configuration or
    trusted proxy metadata and must exactly match the externally configured URL.
    form_parameters are syntactically parsed fields for validators that require
    them; they are NOT business-decoded events. raw_body is always preserved.
    """
    method: str
    public_url: str
    content_type: str
    raw_body: bytes
    headers: Mapping[str, str]
    form_parameters: Mapping[str, str | Sequence[str]] | None = None

    def __post_init__(self):
        if not self.method.strip(): raise ValueError("HTTP method is required")
        if not self.public_url.startswith("https://"): raise ValueError("webhook public_url must use HTTPS")
        if not self.content_type.strip(): raise ValueError("content_type is required")

class WebhookSignatureVerifier(Protocol):
    """Use the provider SDK's exact signature algorithm and request semantics."""
    def verify(self, request: SignedWebhookRequest) -> bool: ...

class BridgeRepository(Protocol):
    """Atomically deduplicate an event and persist its session mutation.

    Production implementations MUST use a database transaction and unique
    (provider, provider_account_id, event_id) constraint. If apply raises, neither write is committed.
    """
    def apply_event_once(self, provider: str, event_id: str, session_id: str,
                         apply: Callable[[BridgeSession], BridgeSession | EventApplication], *,
                         provider_account_id: str = "default", payload_digest: str = "") -> bool: ...
    def get_session(self, session_id: str) -> BridgeSession | None: ...

class BridgeProvider(Protocol):
    """Server-side provider operations. Credentials never leave the backend."""
    def create_bridge(self, *, session_id: str, idempotency_key: str) -> str: ...
    def start_recording(self, *, provider_session_id: str) -> None: ...
    def stop_recording(self, *, provider_session_id: str) -> None: ...
    def close_bridge(self, *, provider_session_id: str) -> None: ...
