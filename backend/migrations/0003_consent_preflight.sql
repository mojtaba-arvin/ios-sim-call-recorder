-- Consent preflight binds every session to a fixed set of opaque participant references.
-- Existing rows remain empty and fail closed when loaded as active sessions; no identity is inferred.
ALTER TABLE bridge_sessions
    ADD COLUMN IF NOT EXISTS expected_participant_refs JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE bridge_sessions
    ADD CONSTRAINT bridge_sessions_expected_participant_refs_array
    CHECK (jsonb_typeof(expected_participant_refs) = 'array');

CREATE INDEX IF NOT EXISTS bridge_sessions_expected_participant_refs_gin
    ON bridge_sessions USING GIN (expected_participant_refs);
