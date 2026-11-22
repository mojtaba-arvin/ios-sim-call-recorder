"""Durable account-scoped admission control for authenticated Twilio callbacks."""
from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any


class WebhookRateLimitStoreUnavailable(RuntimeError):
    """PostgreSQL could not make an authoritative webhook admission decision."""


class PostgresTwilioWebhookRateLimiter:
    """One shared token bucket per configured Twilio provider account."""

    DEFAULT_CAPACITY = 300
    DEFAULT_REFILL_PER_SECOND = 10.0

    def __init__(
        self, *, connect: Callable[[], Any], provider_account_id: str,
        capacity: int = DEFAULT_CAPACITY,
        refill_per_second: float = DEFAULT_REFILL_PER_SECOND,
    ):
        if not isinstance(provider_account_id, str) or not provider_account_id.strip() or len(provider_account_id) > 128:
            raise ValueError("provider_account_id must be a non-empty bounded identifier")
        if not isinstance(capacity, int) or capacity < 1:
            raise ValueError("capacity must be a positive integer")
        if not isinstance(refill_per_second, (int, float)) or refill_per_second <= 0:
            raise ValueError("refill_per_second must be positive")
        self._connect = connect
        self.provider_account_id = provider_account_id
        self.capacity = capacity
        self.refill_per_second = float(refill_per_second)

    def consume(self) -> tuple[bool, int]:
        """Consume one token atomically across all API instances."""
        sql = """
            WITH limits AS (
                SELECT %s::numeric AS capacity, %s::numeric AS refill
            ), tick AS (
                SELECT clock_timestamp() AS at
            )
            INSERT INTO provider_webhook_rate_limits
                (provider, provider_account_id, tokens, updated_at, last_allowed)
            VALUES (
                'twilio', %s,
                (SELECT capacity - 1 FROM limits),
                (SELECT at FROM tick),
                true
            )
            ON CONFLICT (provider, provider_account_id) DO UPDATE SET
                tokens = CASE
                    WHEN LEAST(
                        (SELECT capacity FROM limits),
                        provider_webhook_rate_limits.tokens
                          + GREATEST(0, EXTRACT(EPOCH FROM
                              ((SELECT at FROM tick) - provider_webhook_rate_limits.updated_at)))
                            * (SELECT refill FROM limits)
                    ) >= 1
                    THEN LEAST(
                        (SELECT capacity FROM limits),
                        provider_webhook_rate_limits.tokens
                          + GREATEST(0, EXTRACT(EPOCH FROM
                              ((SELECT at FROM tick) - provider_webhook_rate_limits.updated_at)))
                            * (SELECT refill FROM limits)
                    ) - 1
                    ELSE LEAST(
                        (SELECT capacity FROM limits),
                        provider_webhook_rate_limits.tokens
                          + GREATEST(0, EXTRACT(EPOCH FROM
                              ((SELECT at FROM tick) - provider_webhook_rate_limits.updated_at)))
                            * (SELECT refill FROM limits)
                    )
                END,
                last_allowed = LEAST(
                    (SELECT capacity FROM limits),
                    provider_webhook_rate_limits.tokens
                      + GREATEST(0, EXTRACT(EPOCH FROM
                          ((SELECT at FROM tick) - provider_webhook_rate_limits.updated_at)))
                        * (SELECT refill FROM limits)
                ) >= 1,
                updated_at = (SELECT at FROM tick)
            RETURNING last_allowed, tokens
        """
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (self.capacity, self.refill_per_second, self.provider_account_id))
                    row = cur.fetchone()
                    if row is None:
                        raise RuntimeError("webhook rate-limit upsert returned no row")
                    allowed, tokens = bool(row[0]), float(row[1])
        except Exception as exc:
            raise WebhookRateLimitStoreUnavailable("provider webhook admission decision failed") from exc
        if allowed:
            return True, 0
        return False, max(1, math.ceil((1.0 - tokens) / self.refill_per_second))
