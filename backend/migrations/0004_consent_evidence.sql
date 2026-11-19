-- Persist the signed event and disclosure-policy provenance for every participant consent.
-- The digest is an audit pointer; raw consent media and phone numbers are never stored here.
ALTER TABLE bridge_sessions
    ADD COLUMN IF NOT EXISTS consent_evidence JSONB NOT NULL
    DEFAULT '[]'::jsonb
    CHECK (jsonb_typeof(consent_evidence) = 'array');
