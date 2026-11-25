-- Fenced, retryable claims for external retention deletion.
ALTER TABLE media_assets
    ADD COLUMN IF NOT EXISTS deletion_claim_token UUID,
    ADD COLUMN IF NOT EXISTS deletion_lease_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS deletion_attempts INTEGER NOT NULL DEFAULT 0
        CHECK (deletion_attempts >= 0),
    ADD COLUMN IF NOT EXISTS deletion_next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS deletion_last_error TEXT;

ALTER TABLE media_assets
    DROP CONSTRAINT IF EXISTS media_assets_deletion_lease_pair_check;
ALTER TABLE media_assets
    ADD CONSTRAINT media_assets_deletion_lease_pair_check
    CHECK ((deletion_claim_token IS NULL) = (deletion_lease_expires_at IS NULL));

CREATE INDEX IF NOT EXISTS media_assets_deletion_claim_idx
    ON media_assets (deletion_next_attempt_at, retention_expires_at)
    WHERE deleted_at IS NULL;
