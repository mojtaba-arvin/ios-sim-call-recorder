-- Add tenant ownership for all authenticated session access.
-- Existing pre-tenant rows are isolated under the non-login legacy tenant.
ALTER TABLE bridge_sessions
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'legacy'
    CHECK (length(tenant_id) BETWEEN 1 AND 128);

CREATE INDEX IF NOT EXISTS bridge_sessions_tenant_updated_idx
    ON bridge_sessions (tenant_id, updated_at DESC);
