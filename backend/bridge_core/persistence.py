"""PostgreSQL persistence for sessions, provider receipts and a transactional outbox."""
from __future__ import annotations
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4
from .application import EventApplication, OutboxCommand
from .domain import BridgeSession, ConsentEvidence, InvalidTransition, SessionState

class EventIdentityConflict(ValueError):
    """A provider reused an event ID for a different session."""

class LeaseLost(RuntimeError):
    """An outbox command is no longer leased by the supplied token."""

class ProviderResourceConflict(ValueError):
    """A provider resource identifier is already owned by another mapping."""


class CommandIdentityConflict(ValueError):
    """An idempotency key was reused for a different provider command."""

@dataclass(frozen=True, slots=True)
class DeadLetterCommand:
    command_id: UUID
    command_type: str
    idempotency_key: str
    session_id: str
    provider: str
    provider_account_id: str
    attempts: int
    last_error_code: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class LeasedCommand:
    command_id: UUID
    command_type: str
    idempotency_key: str
    session_id: str
    provider: str
    provider_account_id: str
    payload: Mapping[str, object]
    attempts: int
    lease_token: UUID
    lease_owner: str
    lease_expires_at: datetime

class PostgresBridgeRepository:
    """DB-API-compatible repository backed by psycopg 3 connection factories.

    The caller owns schema migration execution. Every operation owns a short
    transaction; no provider network operation is performed inside it.
    """
    def __init__(self, connect: Callable[[], Any]):
        self._connect = connect

    def create_session(self, session: BridgeSession, *, tenant_id: str = "default") -> None:
        if not tenant_id or not tenant_id.strip() or len(tenant_id) > 128:
            raise ValueError("tenant_id must be a non-empty bounded identifier")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO bridge_sessions
                    (tenant_id, session_id, expected_participants, expected_participant_refs, state,
                     joined_participants, consented_participants, consent_evidence, failure_code, updated_at)
                    VALUES (%s, %s, %s, %s::jsonb, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s)""",
                    (tenant_id, session.session_id, session.expected_participants,
                     json.dumps(sorted(session.expected_participant_refs)), session.state.value,
                     json.dumps(sorted(session.joined_participants)),
                     json.dumps(sorted(session.consented_participants)),
                     json.dumps([item.to_dict() for item in session.consent_evidence]),
                     session.failure_code, session.updated_at),
                )

    def get_session(self, session_id: str, *, tenant_id: str | None = None) -> BridgeSession | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                if tenant_id is None:
                    cur.execute(
                        """SELECT session_id, expected_participants, expected_participant_refs, state,
                        joined_participants, consented_participants, consent_evidence, failure_code, updated_at
                        FROM bridge_sessions WHERE session_id = %s""", (session_id,))
                else:
                    cur.execute(
                        """SELECT session_id, expected_participants, expected_participant_refs, state,
                        joined_participants, consented_participants, consent_evidence, failure_code, updated_at
                        FROM bridge_sessions WHERE session_id = %s AND tenant_id = %s""",
                        (session_id, tenant_id))
                row = cur.fetchone()
        return self._session_from_row(row) if row else None

    def cancel_session(self, session_id: str, *, tenant_id: str) -> BridgeSession:
        """Cancel only before provider side effects can exist; never fake remote closure."""
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id is required")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT session_id, expected_participants, expected_participant_refs, state,
                    joined_participants, consented_participants, consent_evidence, failure_code, updated_at
                    FROM bridge_sessions WHERE session_id = %s AND tenant_id = %s FOR UPDATE""",
                    (session_id, tenant_id))
                row = cur.fetchone()
                if row is None:
                    raise KeyError(session_id)
                current = self._session_from_row(row)
                if current.state is SessionState.CANCELLED:
                    return current
                if current.state not in {SessionState.CREATED, SessionState.AWAITING_USER_ACTION}:
                    raise InvalidTransition("provider activity may already exist; remote close is required")
                updated = current.transition(SessionState.CANCELLED)
                cur.execute(
                    "UPDATE bridge_sessions SET state = %s, updated_at = %s WHERE session_id = %s AND tenant_id = %s",
                    (updated.state.value, updated.updated_at, session_id, tenant_id))
                return updated

    def apply_event_once(
        self, provider: str, event_id: str, session_id: str,
        apply: Callable[[BridgeSession], BridgeSession | EventApplication], *,
        provider_account_id: str = "default", payload_digest: str = "",
    ) -> bool:
        """Deduplicate and atomically persist a transition plus generated commands."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO provider_event_receipts
                    (provider, provider_account_id, event_id, session_id, payload_digest)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (provider, provider_account_id, event_id) DO NOTHING
                    RETURNING event_id""",
                    (provider, provider_account_id, event_id, session_id, payload_digest))
                if cur.fetchone() is None:
                    cur.execute(
                        """SELECT session_id, payload_digest FROM provider_event_receipts
                        WHERE provider = %s AND provider_account_id = %s AND event_id = %s""",
                        (provider, provider_account_id, event_id))
                    existing = cur.fetchone()
                    if (existing is None or existing[0] != session_id
                            or existing[1] != payload_digest):
                        raise EventIdentityConflict("provider event identity conflicts with an existing receipt")
                    return False

                cur.execute(
                    """SELECT session_id, expected_participants, expected_participant_refs, state,
                    joined_participants, consented_participants, consent_evidence, failure_code, updated_at
                    FROM bridge_sessions WHERE session_id = %s FOR UPDATE""", (session_id,))
                row = cur.fetchone()
                if row is None:
                    raise KeyError(session_id)
                current = self._session_from_row(row)
                result = apply(current)
                application = result if isinstance(result, EventApplication) else EventApplication(result)
                updated = application.session
                if updated.session_id != session_id:
                    raise ValueError("event application cannot change the session identity")
                cur.execute(
                    """UPDATE bridge_sessions SET expected_participants = %s, state = %s,
                    joined_participants = %s::jsonb, consented_participants = %s::jsonb,
                    consent_evidence = %s::jsonb, failure_code = %s,
                    updated_at = %s WHERE session_id = %s""",
                    (updated.expected_participants, updated.state.value,
                     json.dumps(sorted(updated.joined_participants)),
                     json.dumps(sorted(updated.consented_participants)),
                     json.dumps([item.to_dict() for item in updated.consent_evidence]),
                     updated.failure_code, updated.updated_at, session_id))
                for command in application.commands:
                    if command.session_id != session_id:
                        raise ValueError("outbox command session_id must match the event session")
                    self._insert_command(cur, command)
                return True

    def enqueue_command(self, command: OutboxCommand) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                return self._insert_command(cur, command)

    @staticmethod
    def _insert_command(cur: Any, command: OutboxCommand) -> bool:
        cur.execute(
            """INSERT INTO outbox_commands
            (command_id, command_type, idempotency_key, session_id, provider,
             provider_account_id, payload, status, attempts, max_attempts, available_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, 'pending', 0, 8, now())
            ON CONFLICT (idempotency_key) DO NOTHING RETURNING command_id""",
            (command.command_id, command.command_type, command.idempotency_key,
             command.session_id, command.provider, command.provider_account_id,
             json.dumps(dict(command.payload), separators=(",", ":"), sort_keys=True)))
        if cur.fetchone() is not None:
            return True
        cur.execute(
            """SELECT command_type, session_id, provider, provider_account_id, payload
            FROM outbox_commands WHERE idempotency_key = %s""",
            (command.idempotency_key,))
        existing = cur.fetchone()
        if existing is None:
            raise RuntimeError("outbox idempotency conflict could not be resolved")
        existing_payload = existing[4] if isinstance(existing[4], dict) else json.loads(existing[4])
        if (existing[0], existing[1], existing[2], existing[3], existing_payload) != (
                command.command_type, command.session_id, command.provider,
                command.provider_account_id, dict(command.payload)):
            raise CommandIdentityConflict("outbox idempotency key conflicts with a different command")
        return False


    def get_provider_resource(self, provider: str, provider_account_id: str,
                              session_id: str) -> str | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT conference_sid FROM provider_resources
                    WHERE provider = %s AND provider_account_id = %s AND session_id = %s""",
                    (provider, provider_account_id, session_id))
                row = cur.fetchone()
        return row[0] if row else None

    def put_provider_resource(self, provider: str, provider_account_id: str,
                              session_id: str, conference_sid: str) -> None:
        for name, value in (("provider", provider), ("provider_account_id", provider_account_id),
                            ("session_id", session_id), ("conference_sid", conference_sid)):
            if not value or not value.strip():
                raise ValueError(f"{name} must not be empty")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO provider_resources
                    (provider, provider_account_id, session_id, conference_sid)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (provider, provider_account_id, session_id) DO NOTHING
                    RETURNING conference_sid""",
                    (provider, provider_account_id, session_id, conference_sid))
                inserted = cur.fetchone()
                if inserted is not None:
                    return
                cur.execute(
                    """SELECT conference_sid FROM provider_resources
                    WHERE provider = %s AND provider_account_id = %s AND session_id = %s""",
                    (provider, provider_account_id, session_id))
                existing = cur.fetchone()
                if existing is None or existing[0] != conference_sid:
                    raise ProviderResourceConflict(
                        "session is already mapped to a different provider conference")

    def get_provider_participant_resource(self, provider: str, provider_account_id: str,
                                          session_id: str, participant_ref: str) -> str | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT call_sid FROM provider_participant_resources
                    WHERE provider = %s AND provider_account_id = %s
                    AND session_id = %s AND participant_ref = %s""",
                    (provider, provider_account_id, session_id, participant_ref))
                row = cur.fetchone()
        return row[0] if row else None

    def put_provider_participant_resource(self, provider: str, provider_account_id: str,
                                          session_id: str, participant_ref: str,
                                          call_sid: str) -> None:
        for name, value in (("provider", provider), ("provider_account_id", provider_account_id),
                            ("session_id", session_id), ("participant_ref", participant_ref),
                            ("call_sid", call_sid)):
            if not value or not value.strip():
                raise ValueError(f"{name} must not be empty")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO provider_participant_resources
                    (provider, provider_account_id, session_id, participant_ref, call_sid)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (provider, provider_account_id, session_id, participant_ref)
                    DO NOTHING RETURNING call_sid""",
                    (provider, provider_account_id, session_id, participant_ref, call_sid))
                inserted = cur.fetchone()
                if inserted is not None:
                    return
                cur.execute(
                    """SELECT call_sid FROM provider_participant_resources
                    WHERE provider = %s AND provider_account_id = %s
                    AND session_id = %s AND participant_ref = %s""",
                    (provider, provider_account_id, session_id, participant_ref))
                existing = cur.fetchone()
                if existing is None or existing[0] != call_sid:
                    raise ProviderResourceConflict(
                        "participant is already mapped to a different provider call")

    def claim_outbox(self, *, worker_id: str, limit: int = 10,
                     lease_seconds: int = 30) -> tuple[LeasedCommand, ...]:
        if not worker_id.strip():
            raise ValueError("worker_id must not be empty")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        if not 1 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds must be between 1 and 3600")
        claimed: list[LeasedCommand] = []
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE outbox_commands SET status = 'dead', lease_owner = NULL,
                    lease_token = NULL, lease_expires_at = NULL,
                    last_error_code = 'lease_expired_max_attempts'
                    WHERE status = 'leased' AND lease_expires_at <= now()
                    AND attempts >= max_attempts""")
                cur.execute(
                    """SELECT command_id, command_type, idempotency_key, session_id,
                    provider, provider_account_id, payload, attempts
                    FROM outbox_commands WHERE attempts < max_attempts
                    AND ((status = 'pending' AND available_at <= now())
                         OR (status = 'leased' AND lease_expires_at <= now()))
                    ORDER BY available_at, created_at, command_id
                    LIMIT %s FOR UPDATE SKIP LOCKED""", (limit,))
                rows = cur.fetchall()
                for row in rows:
                    token = uuid4()
                    cur.execute(
                        """UPDATE outbox_commands SET status = 'leased', attempts = attempts + 1,
                        lease_owner = %s, lease_token = %s,
                        lease_expires_at = now() + (%s * interval '1 second')
                        WHERE command_id = %s RETURNING lease_expires_at, attempts""",
                        (worker_id, token, lease_seconds, row[0]))
                    lease = cur.fetchone()
                    payload = row[6] if isinstance(row[6], dict) else json.loads(row[6])
                    claimed.append(LeasedCommand(
                        command_id=row[0], command_type=row[1], idempotency_key=row[2],
                        session_id=row[3], provider=row[4], provider_account_id=row[5],
                        payload=payload, attempts=lease[1], lease_token=token,
                        lease_owner=worker_id, lease_expires_at=lease[0]))
        return tuple(claimed)

    def acknowledge_outbox(self, command_id: UUID, lease_token: UUID) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE outbox_commands SET status = 'delivered', delivered_at = now(),
                    lease_owner = NULL, lease_token = NULL, lease_expires_at = NULL
                    WHERE command_id = %s AND status = 'leased' AND lease_token = %s""",
                    (command_id, lease_token))
                if cur.rowcount != 1:
                    raise LeaseLost("outbox lease is no longer owned by this worker")

    def fail_outbox(self, command_id: UUID, lease_token: UUID, *,
                    error_code: str, retry_delay_seconds: int, terminal: bool = False) -> str:
        if not re.fullmatch(r"[a-z0-9_.-]{1,64}", error_code):
            raise ValueError("error_code must be a stable, non-sensitive identifier")
        if not 0 <= retry_delay_seconds <= 86400:
            raise ValueError("retry_delay_seconds must be between 0 and 86400")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE outbox_commands
                    SET status = CASE WHEN %s OR attempts >= max_attempts THEN 'dead' ELSE 'pending' END,
                    available_at = now() + (%s * interval '1 second'), last_error_code = %s,
                    lease_owner = NULL, lease_token = NULL, lease_expires_at = NULL
                    WHERE command_id = %s AND status = 'leased' AND lease_token = %s
                    RETURNING status""",
                    (terminal, retry_delay_seconds, error_code, command_id, lease_token))
                row = cur.fetchone()
                if row is None:
                    raise LeaseLost("outbox lease is no longer owned by this worker")
                return row[0]

    def list_dead_letters(self, *, limit: int = 100) -> tuple[DeadLetterCommand, ...]:
        """Return redacted dead-letter metadata; payloads and provider data are omitted."""
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT command_id, command_type, idempotency_key, session_id,
                    provider, provider_account_id, attempts, last_error_code, created_at
                    FROM outbox_commands WHERE status = 'dead'
                    ORDER BY created_at, command_id LIMIT %s""",
                    (limit,))
                rows = cur.fetchall()
        return tuple(DeadLetterCommand(*row) for row in rows)

    @staticmethod
    def _session_from_row(row: tuple[Any, ...]) -> BridgeSession:
        expected = row[2] if isinstance(row[2], list) else json.loads(row[2])
        joined = row[4] if isinstance(row[4], list) else json.loads(row[4])
        consented = row[5] if isinstance(row[5], list) else json.loads(row[5])
        evidence = row[6] if isinstance(row[6], list) else json.loads(row[6])
        return BridgeSession(
            session_id=row[0], expected_participants=row[1],
            expected_participant_refs=frozenset(expected), state=SessionState(row[3]),
            joined_participants=frozenset(joined), consented_participants=frozenset(consented),
            consent_evidence=tuple(ConsentEvidence.from_dict(item) for item in evidence),
            failure_code=row[7], updated_at=row[8])
