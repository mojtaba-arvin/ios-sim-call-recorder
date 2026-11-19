---
name: backend-validation
description: Validate backend state transitions, persistence, webhooks, provider dispatch, concurrency, retries and tenant isolation.
---

# Backend validation

## Procedure
1. Identify API contracts, state machine transitions and persistence invariants.
2. Test success, invalid input, duplicate delivery, conflicting idempotency keys and authorization failures.
3. Exercise concurrent updates, transaction rollback and process-crash windows.
4. Verify outbox lease expiry, retry limits, dead-letter handling and token-checked acknowledgements.
5. Verify webhook signature, timestamp/replay handling and secret rotation behavior.
6. Test tenant isolation at query and database-constraint levels.
7. Exercise provider outcomes APPLIED, NOT_APPLIED and UNKNOWN; never equate a timeout with failure.
8. Inspect logs, metrics and traces for secrets, phone numbers, recordings and raw provider payloads.
9. Run migration forward/rollback checks and document irreversible operations.

## Output
- Test matrix with expected/actual state transitions.
- Database and concurrency evidence.
- Provider sandbox scope and explicit non-production caveats.
- Recovery and rollback findings.

## Completion gate
No claim of exactly-once execution; demonstrate idempotent effects and recoverable uncertainty.
