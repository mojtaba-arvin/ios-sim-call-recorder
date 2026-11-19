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

Apply SQL migrations in numeric order with the deployment migration runner before starting the
service: `0001_bridge_persistence.sql`, then `0002_provider_resources.sql`. The repository deliberately
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
reclaimed; attempts are bounded and terminal provider failures can be moved directly
to `dead` without a retry delay.

A worker must commit the lease before calling a provider, pass the stable
`idempotency_key` when supported, reconcile uncertain outcomes before retrying
non-idempotent side effects, and acknowledge only after observing acceptance.
Persist only stable error codes, never exception text or raw provider payloads.

This is at-least-once command delivery, not exactly-once remote execution. A
worker can crash after a provider side effect and before acknowledgement commits.
Provider-side idempotency/reconciliation is mandatory before enabling live calls.

## Provider command dispatcher foundation

`bridge_core.dispatcher.OutboxCommandDispatcher` leases commands and invokes a configured
provider/account adapter only after the lease transaction has committed. Every delivery
attempt first calls the adapter's `reconcile` method with the persisted Conference SID
and, when the command carries an opaque `participant_ref`, its mapped Call SID. The
adapter must return `UNKNOWN` rather than execute when provider state cannot be established.
Only `NOT_APPLIED` permits execution; `APPLIED` is acknowledged without replaying the
side effect. Provider I/O must never run inside a repository transaction.

Before reconciliation, `participant.add` commands must contain a non-empty opaque `participant_ref` (at most 128 characters and no whitespace). Invalid references are dead-lettered before provider I/O so malformed outbox data cannot create an untracked provider leg.

The `0002_provider_resources.sql` migration stores provider/account/session-scoped
Conference SIDs and opaque participant-reference-to-Call-SID mappings. These identifiers
are immutable for a given mapping; conflicts fail closed. Do not store phone numbers,
provider credentials, media URLs, audio, or signatures in these tables or outbox payloads.

The parallel provider/platform evidence and open questions are recorded in
[`docs/research/provider-evaluation-2026-11.md`](../docs/research/provider-evaluation-2026-11.md).

This is a dispatcher contract and persistence foundation, not a live Twilio adapter.
Twilio participant creation does not have a documented general idempotency guarantee in
the reviewed API reference. A concrete adapter must use a stable provider correlation
strategy and query provider state before retrying ambiguous operations. No real provider
calls or carrier-compatibility claims are made by these tests.

## Twilio recording and consent ordering

The current domain reducer is provider-neutral and accepts consent after all participants have joined, then emits a `recording.start` command. **That event order is not yet a valid Twilio Conference implementation.** Twilio exposes conference recording-from-start configuration when a participant joins/creates the conference; the reviewed API documents pause/resume for an existing Conference recording, but not a general start operation after join or a stop operation for Conference recordings. See [ADR-0002](../docs/engineering/adr-0002-twilio-recording-consent-order.md).

A concrete Twilio adapter must therefore collect and persist affirmative consent for every expected participant before the first recording-enabled participant is joined. It must create/join the conference with recording enabled from the start, and use pause/resume or conference closure rather than an unsupported recording-stop call. The current state machine must be redesigned before a live Twilio adapter is enabled.

The manual carrier-merge path is separately blocked: a merged cellular call may arrive as one mixed PSTN participant, so the remote party cannot be assumed to be separately addressable or consent-verified. No provider adapter, live recording or carrier support is claimed.

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


The outbox payload validator rejects phone-number fields and common telephony aliases (`from`, `to`, `caller`, `callee`, `destination`, E.164 and nested equivalents) so alternate key names cannot bypass the PII boundary.
