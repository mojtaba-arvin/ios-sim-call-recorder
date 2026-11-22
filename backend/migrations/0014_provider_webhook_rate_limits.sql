-- Durable rate limiting for callbacks authenticated by the configured provider signature.
-- Account identity comes from deployment configuration, never callback-supplied fields.
CREATE TABLE IF NOT EXISTS provider_webhook_rate_limits (
    provider TEXT NOT NULL CHECK (provider = 'twilio'),
    provider_account_id TEXT NOT NULL
        CHECK (length(provider_account_id) BETWEEN 1 AND 128),
    tokens NUMERIC(12, 6) NOT NULL CHECK (tokens >= 0),
    updated_at TIMESTAMPTZ NOT NULL,
    last_allowed BOOLEAN NOT NULL,
    PRIMARY KEY (provider, provider_account_id)
);

CREATE INDEX IF NOT EXISTS provider_webhook_rate_limits_updated_idx
    ON provider_webhook_rate_limits (updated_at);
