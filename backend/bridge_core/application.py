"""Atomic domain applications and provider-command outbox records."""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from typing import Mapping
from uuid import UUID, uuid4
from .domain import BridgeSession

_SENSITIVE_KEYS = {
    "phone", "phonenumber", "callerid", "authorization", "authtoken",
    "token", "signature", "mediaurl", "audiourl", "recordingurl",
    "password", "secret", "audio", "transcript",
}

def _validate_payload(value: object) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if normalized in _SENSITIVE_KEYS:
                raise ValueError(f"sensitive outbox payload field is forbidden: {normalized}")
            _validate_payload(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _validate_payload(child)

@dataclass(frozen=True, slots=True)
class OutboxCommand:
    command_type: str
    idempotency_key: str
    session_id: str
    provider: str
    provider_account_id: str = "default"
    payload: Mapping[str, object] = field(default_factory=dict)
    command_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        for name in ("command_type", "idempotency_key", "session_id", "provider", "provider_account_id"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must not be empty")
        _validate_payload(self.payload)
        try:
            json.dumps(dict(self.payload), separators=(",", ":"), sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise ValueError("outbox payload must be JSON serializable") from exc

@dataclass(frozen=True, slots=True)
class EventApplication:
    session: BridgeSession
    commands: tuple[OutboxCommand, ...] = ()
