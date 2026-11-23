# Outbox worker reliability runbook

**Current implementation:** lease-based PostgreSQL outbox, provider reconciliation before side effects, bounded polling worker.  
**Status:** software controls exist; live Twilio side effects remain disabled until external gates pass.

## Lease and batch contract

- The production entry point sets a 60-second command lease and the Twilio SDK client uses a 10-second HTTP timeout.
- Dispatch is sequential inside a claimed batch. A batch of 10 can leave later commands waiting while earlier commands perform provider reconciliation and execution, consuming their lease before they start.
- The runtime default is therefore set to `WORKER_BATCH_SIZE=1`. This reduces lease starvation but does not establish exactly-once provider effects.
- Do not raise batch size until lease renewal is implemented or a measured worst-case reconciliation + execution bound (with margin) is proven below the lease duration.
- A lease-token mismatch must prevent stale acknowledgement/failure updates. Expired leases are eligible for reclamation; the provider adapter must reconcile before any repeat side effect.

## Retry / reconciliation contract

1. Claim commands transactionally and commit before provider I/O.
2. Reconcile provider resources before executing any command.
3. `APPLIED` means persist discovered resource IDs and acknowledge.
4. `NOT_APPLIED` means execute only when the adapter can prove the previous side effect did not happen.
5. `UNKNOWN` means defer for reconciliation; never blindly retry a non-idempotent provider operation.
6. Persist resource mappings before acknowledging the outbox row.
7. Keep consent-call SIDs separate from Conference participant call SIDs.
8. Do not claim exactly-once remote execution. Database idempotency and provider-side idempotency are different guarantees.

## Operational observability

The worker emits sanitized cycle logs with worker ID, claimed count, acknowledged count, deferred count and cycle duration in milliseconds. It emits a generic cycle-failed event without exception text.

Never log command payloads, participant addresses, phone numbers, Twilio credentials, Call/Conference/Recording SIDs, callback bodies or signed media URLs.

Before staging, add/verify durable metrics and alerts for:

- oldest pending outbox age and pending count
- expired lease count and reclaim rate
- retry/deferred count by sanitized error code
- dead-letter count and age
- unknown reconciliation count and age
- provider request latency / timeout / 429 / 5xx
- command execution duration versus lease duration
- worker heartbeat and cycle failures
- consent-to-conference transition failures
- retention deletion backlog and age

Metrics must use bounded labels (provider, operation, stable error code); never use session IDs, tenant IDs, phone numbers or provider SIDs as metric labels.

## Safe local verification

```sh
PYTHONPATH=backend python -m unittest backend.tests.test_worker backend.tests.test_dispatcher -v
PYTHONPATH=backend python -m unittest discover -s backend/tests -v
```

CI should run these on PostgreSQL 16 and 17 through Release Preflight. The local unit tests do not make live provider calls.

## Release boundary

No Twilio call, AWS resource, production worker, alert destination or paid service is provisioned by this runbook. Live staging acceptance requires explicit account authorization, two consenting test participants, approved disclosure and a bounded test budget.
