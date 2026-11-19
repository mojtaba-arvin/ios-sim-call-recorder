-- Provider resource ownership is scoped by provider account and internal session.
-- Only opaque provider identifiers and opaque participant references are stored.
CREATE TABLE IF NOT EXISTS provider_resources (
    provider TEXT NOT NULL,
    provider_account_id TEXT NOT NULL,
    session_id TEXT NOT NULL REFERENCES bridge_sessions(session_id),
    conference_sid TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (provider, provider_account_id, session_id),
    UNIQUE (provider, provider_account_id, conference_sid)
);

CREATE TABLE IF NOT EXISTS provider_participant_resources (
    provider TEXT NOT NULL,
    provider_account_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    participant_ref TEXT NOT NULL,
    call_sid TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (provider, provider_account_id, session_id, participant_ref),
    UNIQUE (provider, provider_account_id, call_sid),
    FOREIGN KEY (provider, provider_account_id, session_id)
        REFERENCES provider_resources(provider, provider_account_id, session_id)
        ON DELETE CASCADE
);
