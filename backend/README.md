# Conference Bridge Backend Core

This is a provider-neutral domain and persistence foundation, not a deployable
recording service and not a real PSTN provider integration.

## Included
- Typed bridge lifecycle and guarded transitions.
- Consent from every expected, joined participant before recording can start.
- Provider-native signature verification using the exact request URL, method,
  content type, headers, original bytes and (where required) parsed form fields.
- Provider event deduplication scoped by provider and provider account.
- Atomic session transition and transactional outbox command insertion.
- PostgreSQL-backed durable sessions, event receipts and outbox leases.
- Bounded retries, lease-token ownership and dead-letter state.
- Opaque participant references rather than phone numbers.

## Persistence and migrations

PostgreSQL 16 is the CI integration-test target. Install the pinned backend dependencies (PostgreSQL driver and Twilio webhook SDK):

```sh
python -m pip install -r backend/requirements.txt
```

Apply SQL migrations with the deployment migration runner before starting the
service. The initial schema is
`backend/migrations/0001_bridge_persistence.sql`. The repository deliberately
does not run DDL automatically at application startup.

Construct the repository with a connection factory:

```python
import os
import psycopg
from bridge_core.persistence import PostgresBridgeRepository

repository = PostgresBridgeRepository(
    lambda: psycopg.connect(os.environ["DATABASE_URL"])
)
```

Each repository operation owns a short transaction. Event receipt insertion,
session row locking/update and outbox command insertion commit or roll back as
one unit. Event identity is unique by
`(provider, provider_account_id, event_id)`; reusing an event ID for a different
session is rejected.

## Outbox worker contract

Workers call `claim_outbox` to lease commands. Claims use PostgreSQL
`FOR UPDATE SKIP LOCKED`, an expiring lease and a fresh opaque lease token.
Only the current token can acknowledge or fail a command. Expired leases can be
reclaimed; attempts are bounded and terminal commands move to `dead`.

A worker must commit the lease before calling a provider, pass the stable
`idempotency_key` when supported, reconcile uncertain outcomes before retrying
non-idempotent side effects, and acknowledge only after observing acceptance.
Persist only stable error codes, never exception text or raw provider payloads.

This is at-least-once command delivery, not exactly-once remote execution. A
worker can crash after a provider side effect and before acknowledgement commits.
Provider-side idempotency/reconciliation is mandatory before enabling live calls.

## Security and deliberate production gaps

Never persist raw phone numbers, credentials, signatures, media URLs or audio in
event/outbox payloads or logs. Use opaque participant/session references. Keep
provider credentials in a secret manager.

No production HTTP endpoint, authentication, rate limiting, trusted public URL
reconstruction, provider API client, media ingestion, audio verification,
object storage, retention worker or deletion integration is implemented. The
in-memory repository is test-only. No carrier three-way-call compatibility or
real two-way recording is proven.

## Tests

```sh
PYTHONPATH=backend python -m unittest discover -s backend/tests -v
```

PostgreSQL integration tests require `TEST_DATABASE_URL`. They cover rollback,
duplicate/concurrent delivery, account-scoped event identity, atomic outbox
insertion, concurrent claims, lease expiry, stale lease rejection and retries.
