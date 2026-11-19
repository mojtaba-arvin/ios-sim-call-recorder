"""Test-only in-memory repository; never use for production persistence."""
from __future__ import annotations
from collections.abc import Callable
from threading import RLock
from .application import EventApplication
from .domain import BridgeSession

class InMemoryBridgeRepository:
    def __init__(self):
        self._sessions: dict[str, BridgeSession] = {}
        self._events: set[tuple[str, str, str]] = set()
        self._outbox: dict[str, object] = {}
        self._lock = RLock()

    def add_session(self, session: BridgeSession) -> None:
        with self._lock:
            if session.session_id in self._sessions: raise ValueError("session already exists")
            self._sessions[session.session_id] = session

    def set_session_for_test(self, session: BridgeSession) -> None:
        with self._lock: self._sessions[session.session_id] = session

    def get_session(self, session_id: str) -> BridgeSession | None:
        with self._lock: return self._sessions.get(session_id)

    def apply_event_once(self, provider: str, event_id: str, session_id: str,
                         apply: Callable[[BridgeSession], BridgeSession | EventApplication], *,
                         provider_account_id: str = "default", payload_digest: str = "") -> bool:
        key = (provider, provider_account_id, event_id)
        with self._lock:
            if key in self._events: return False
            result = apply(self._sessions[session_id])
            application = result if isinstance(result, EventApplication) else EventApplication(result)
            self._sessions[session_id] = application.session
            for command in application.commands:
                existing = self._outbox.get(command.idempotency_key)
                if existing is not None and (
                    existing.command_type, existing.session_id, existing.provider,
                    existing.provider_account_id, dict(existing.payload)
                ) != (
                    command.command_type, command.session_id, command.provider,
                    command.provider_account_id, dict(command.payload)
                ):
                    raise ValueError("outbox idempotency key conflicts with a different command")
                self._outbox.setdefault(command.idempotency_key, command)
            self._events.add(key)
            return True

    def get_outbox_commands(self) -> tuple[object, ...]:
        with self._lock:
            return tuple(self._outbox.values())
