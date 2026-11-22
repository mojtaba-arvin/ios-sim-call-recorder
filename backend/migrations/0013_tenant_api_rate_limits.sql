-- Shared, durable token buckets for authenticated tenant API traffic.
-- One row per tenant and route class; PostgreSQL upserts serialize concurrent instances.
CREATE TABLE IF NOT EXISTS tenant_api_rate_limits (
    tenant_id TEXT NOT NULL CHECK (length(tenant_id) BETWEEN 1 AND 128),
    bucket TEXT NOT NULL CHECK (bucket IN ('read', 'write')),
    tokens NUMERIC(12, 6) NOT NULL CHECK (tokens >= 0),
    updated_at TIMESTAMPTZ NOT NULL,
    last_allowed BOOLEAN NOT NULL,
    PRIMARY KEY (tenant_id, bucket)
);

CREATE INDEX IF NOT EXISTS tenant_api_rate_limits_updated_idx
    ON tenant_api_rate_limits (updated_at);
