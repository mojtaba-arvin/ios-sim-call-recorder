-- Audit tenant-scoped participant address provisioning without retaining plaintext.
CREATE TABLE IF NOT EXISTS participant_address_audit (
    audit_id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL CHECK (length(tenant_id) BETWEEN 1 AND 128),
    participant_ref TEXT NOT NULL CHECK (length(participant_ref) BETWEEN 1 AND 128),
    action TEXT NOT NULL CHECK (action IN ('created', 'replaced', 'deleted')),
    actor_tenant_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS participant_address_audit_lookup_idx
    ON participant_address_audit (tenant_id, participant_ref, created_at DESC);
