-- Verified Twilio media metadata and two-phase retention deletion.
CREATE TABLE IF NOT EXISTS media_assets (
    media_id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL CHECK (length(tenant_id) BETWEEN 1 AND 128),
    session_id TEXT NOT NULL REFERENCES bridge_sessions(session_id),
    provider TEXT NOT NULL,
    provider_account_id TEXT NOT NULL,
    provider_recording_sid TEXT NOT NULL,
    object_key TEXT,
    sha256 TEXT NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    byte_count BIGINT NOT NULL CHECK (byte_count > 0),
    duration_seconds DOUBLE PRECISION NOT NULL CHECK (duration_seconds > 0),
    sample_rate_hz INTEGER NOT NULL CHECK (sample_rate_hz >= 8000),
    channel_count SMALLINT NOT NULL CHECK (channel_count BETWEEN 1 AND 2),
    channel_activity JSONB NOT NULL CHECK (jsonb_typeof(channel_activity) = 'array'),
    channel_map JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(channel_map) IN ('array', 'object')),
    verification_state TEXT NOT NULL CHECK (verification_state IN ('verified', 'rejected')),
    validation_error TEXT,
    retention_expires_at TIMESTAMPTZ NOT NULL,
    twilio_deleted_at TIMESTAMPTZ,
    object_deleted_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, provider_account_id, provider_recording_sid),
    UNIQUE (object_key)
);
CREATE INDEX IF NOT EXISTS media_assets_retention_idx
    ON media_assets (retention_expires_at)
    WHERE deleted_at IS NULL;
