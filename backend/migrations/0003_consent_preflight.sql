-- Consent preflight binds every session to a fixed set of opaque participant references.
-- Existing rows receive an empty array and fail closed when loaded as active sessions;
-- no participant identity is inferred for pre-migration sessions.
ALTER TABLE bridge_sessions
    ADD COLUMN IF NOT EXISTS expected_participant_refs JSONB NOT NULL
    DEFAULT '[]'::jsonb
    CHECK (jsonb_typeof(expected_participant_refs) = 'array');
