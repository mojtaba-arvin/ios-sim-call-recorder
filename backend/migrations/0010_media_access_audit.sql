CREATE TABLE IF NOT EXISTS media_access_audit (
    audit_id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL CHECK (length(tenant_id) BETWEEN 1 AND 128),
    session_id TEXT NOT NULL REFERENCES bridge_sessions(session_id),
    media_id UUID NOT NULL REFERENCES media_assets(media_id),
    action TEXT NOT NULL CHECK (action = 'download_url_issued'),
    expires_in_seconds SMALLINT NOT NULL CHECK (expires_in_seconds BETWEEN 60 AND 300),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS media_access_audit_lookup_idx
    ON media_access_audit (tenant_id, session_id, created_at DESC);
