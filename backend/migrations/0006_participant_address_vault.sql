-- Participant addresses are encrypted before insertion; tenant and opaque ref
-- are the only lookup key. No plaintext phone numbers are stored in PostgreSQL.
CREATE TABLE IF NOT EXISTS participant_address_vault (
    tenant_id TEXT NOT NULL CHECK (length(tenant_id) BETWEEN 1 AND 128),
    participant_ref TEXT NOT NULL CHECK (length(participant_ref) BETWEEN 1 AND 128),
    ciphertext BYTEA NOT NULL CHECK (octet_length(ciphertext) >= 29),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, participant_ref)
);
