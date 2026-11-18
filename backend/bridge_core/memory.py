"""Test-only in-memory repository; never use for production persistence."""
from __future__ import annotations
from collections.abc import Callable
from threading import RLock
from .domain import BridgeSession

class InMemoryBridgeRepository:
    def __init__(self):
        self._sessions: dict[str, BridgeSession] = {}
        self._events: set[tuple[str, str]] = set()
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
                         apply: Callable[[BridgeSession], BridgeSession]) -> bool:
        key = (provider, event_id)
        with self._lock:
            if key in self._events: return False
            updated = apply(self._sessions[session_id])
            self._sessions[session_id] = updated
            self._events.add(key)
            return True
