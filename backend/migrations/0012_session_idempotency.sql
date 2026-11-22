-- Durable tenant-scoped idempotency for bridge-session creation.
-- A deferred FK lets the unique idempotency claim serialize concurrent requests
-- before the corresponding session row is inserted in the same transaction.
CREATE UNIQUE INDEX IF NOT EXISTS bridge_sessions_tenant_session_unique_idx
    ON bridge_sessions (tenant_id, session_id);

CREATE TABLE IF NOT EXISTS session_idempotency_keys (
    tenant_id TEXT NOT NULL CHECK (length(tenant_id) BETWEEN 1 AND 128),
    idempotency_key TEXT NOT NULL
        CHECK (idempotency_key ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'),
    request_digest TEXT NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    session_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, idempotency_key),
    CONSTRAINT session_idempotency_session_fk
        FOREIGN KEY (tenant_id, session_id)
        REFERENCES bridge_sessions (tenant_id, session_id)
        DEFERRABLE INITIALLY DEFERRED,
    CHECK (expires_at > created_at)
);

CREATE INDEX IF NOT EXISTS session_idempotency_expiry_idx
    ON session_idempotency_keys (expires_at);
