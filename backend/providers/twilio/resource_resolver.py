"""Account-scoped lookup of signed Twilio callback resource identifiers."""
from __future__ import annotations

from bridge_core.persistence import ProviderResourceConflict


class PostgresTwilioResourceResolver:
    def __init__(self, *, connect, provider_account_id: str):
        if not provider_account_id or not provider_account_id.strip():
            raise ValueError("provider_account_id is required")
        self._connect = connect
        self.provider_account_id = provider_account_id

    def __call__(self, call_sid: str | None, conference_sid: str | None) -> tuple[str, str | None]:
        if not call_sid and not conference_sid:
            raise LookupError("provider resource identity is missing")
        session_from_call = None
        participant_ref = None
        session_from_conference = None
        with self._connect() as conn:
            with conn.cursor() as cur:
                if call_sid:
                    cur.execute(
                        """SELECT session_id, participant_ref
                           FROM provider_participant_resources
                           WHERE provider='twilio' AND provider_account_id=%s AND call_sid=%s
                           UNION ALL
                           SELECT session_id, participant_ref
                           FROM provider_consent_call_resources
                           WHERE provider='twilio' AND provider_account_id=%s AND call_sid=%s""",
                        (self.provider_account_id, call_sid, self.provider_account_id, call_sid),
                    )
                    rows = cur.fetchall()
                    if len(rows) > 1:
                        raise ProviderResourceConflict("Twilio Call SID has multiple internal owners")
                    if rows:
                        session_from_call, participant_ref = rows[0]
                if conference_sid:
                    cur.execute(
                        """SELECT session_id FROM provider_resources
                           WHERE provider='twilio' AND provider_account_id=%s AND conference_sid=%s""",
                        (self.provider_account_id, conference_sid),
                    )
                    row = cur.fetchone()
                    if row:
                        session_from_conference = row[0]
                if call_sid and session_from_call is None:
                    raise LookupError("unmapped Twilio Call SID")
                if conference_sid and session_from_conference is None and session_from_call is None:
                    raise LookupError("unmapped Twilio Conference SID")
                if session_from_call and session_from_conference and session_from_call != session_from_conference:
                    raise ProviderResourceConflict("Twilio resources resolve to different sessions")
                session_id = session_from_call or session_from_conference
                if conference_sid and session_from_call and session_from_conference is None:
                    cur.execute(
                        """INSERT INTO provider_resources
                           (provider, provider_account_id, session_id, conference_sid)
                           VALUES ('twilio', %s, %s, %s)
                           ON CONFLICT (provider, provider_account_id, session_id) DO NOTHING""",
                        (self.provider_account_id, session_id, conference_sid),
                    )
                    cur.execute(
                        """SELECT conference_sid FROM provider_resources
                           WHERE provider='twilio' AND provider_account_id=%s AND session_id=%s""",
                        (self.provider_account_id, session_id),
                    )
                    existing = cur.fetchone()
                    if existing is None or existing[0] != conference_sid:
                        raise ProviderResourceConflict("Twilio conference mapping is immutable")
        return session_id, participant_ref

    def expected_participants(self, session_id: str) -> tuple[str, ...]:
        import json
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT expected_participant_refs FROM bridge_sessions WHERE session_id=%s", (session_id,))
                row = cur.fetchone()
        if row is None:
            raise LookupError("session does not exist")
        values = row[0] if isinstance(row[0], list) else json.loads(row[0])
        return tuple(sorted(values))

    def tenant_for_session(self, session_id: str) -> str:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT tenant_id FROM bridge_sessions WHERE session_id=%s", (session_id,))
                row = cur.fetchone()
        if row is None:
            raise LookupError("session does not exist")
        return row[0]
