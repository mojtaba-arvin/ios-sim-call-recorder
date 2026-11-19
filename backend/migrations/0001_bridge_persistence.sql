-- PostgreSQL 16+; apply before serving traffic.
CREATE TABLE IF NOT EXISTS bridge_sessions (
    session_id TEXT PRIMARY KEY,
    expected_participants INTEGER NOT NULL CHECK (expected_participants >= 2),
    state TEXT NOT NULL,
    joined_participants JSONB NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(joined_participants) = 'array'),
    consented_participants JSONB NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(consented_participants) = 'array'),
    failure_code TEXT,
    updated_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS provider_event_receipts (
    provider TEXT NOT NULL,
    provider_account_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    session_id TEXT NOT NULL REFERENCES bridge_sessions(session_id),
    payload_digest TEXT NOT NULL DEFAULT '',
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (provider, provider_account_id, event_id)
);
CREATE TABLE IF NOT EXISTS outbox_commands (
    command_id UUID PRIMARY KEY,
    command_type TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    session_id TEXT NOT NULL REFERENCES bridge_sessions(session_id),
    provider TEXT NOT NULL,
    provider_account_id TEXT NOT NULL,
    payload JSONB NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    status TEXT NOT NULL CHECK (status IN ('pending', 'leased', 'delivered', 'dead')),
    attempts INTEGER NOT NULL CHECK (attempts >= 0),
    max_attempts INTEGER NOT NULL CHECK (max_attempts > 0),
    available_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    lease_owner TEXT,
    lease_token UUID,
    lease_expires_at TIMESTAMPTZ,
    last_error_code TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    delivered_at TIMESTAMPTZ,
    CHECK ((status = 'leased' AND lease_owner IS NOT NULL AND lease_token IS NOT NULL
            AND lease_expires_at IS NOT NULL)
        OR (status <> 'leased' AND lease_owner IS NULL AND lease_token IS NULL
            AND lease_expires_at IS NULL))
);
CREATE INDEX IF NOT EXISTS outbox_commands_ready_idx
    ON outbox_commands (available_at, created_at)
    WHERE status IN ('pending', 'leased');
