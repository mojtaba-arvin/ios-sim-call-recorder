-- Keep short-lived consent IVR calls separate from Conference participant call legs.
CREATE TABLE IF NOT EXISTS provider_consent_call_resources (
    provider TEXT NOT NULL,
    provider_account_id TEXT NOT NULL,
    session_id TEXT NOT NULL REFERENCES bridge_sessions(session_id),
    participant_ref TEXT NOT NULL,
    call_sid TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (provider, provider_account_id, session_id, participant_ref),
    UNIQUE (provider, provider_account_id, call_sid)
);
