-- Durable, leased Twilio recording ingestion and bounded recovery.
CREATE TABLE IF NOT EXISTS media_ingestions (
    ingestion_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,
    provider_account_id TEXT NOT NULL,
    provider_recording_sid TEXT NOT NULL,
    media_id UUID NOT NULL,
    tenant_id TEXT NOT NULL CHECK (length(tenant_id) BETWEEN 1 AND 128),
    session_id TEXT NOT NULL REFERENCES bridge_sessions(session_id),
    object_key TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('pending','processing','retry','verified','rejected','manual_cleanup')),
    claim_token UUID,
    lease_expires_at TIMESTAMPTZ,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    cleanup_required BOOLEAN NOT NULL DEFAULT false,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, provider_account_id, provider_recording_sid),
    CHECK ((state = 'processing') = (claim_token IS NOT NULL AND lease_expires_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS media_ingestions_recovery_idx
    ON media_ingestions (next_attempt_at, updated_at)
    WHERE state IN ('retry','processing');
CREATE INDEX IF NOT EXISTS media_ingestions_cleanup_idx
    ON media_ingestions (updated_at)
    WHERE cleanup_required = true;
