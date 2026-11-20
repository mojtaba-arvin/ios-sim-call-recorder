# Operations runbook — pre-production backend foundation

**Status:** operational procedure template for future staging. No staging or production environment is currently deployed.

## Safety posture

- Do not enable live PSTN calls or recording with the current repository baseline.
- Keep API and provider credentials in a secret manager; never in GitHub variables visible to untrusted workflows, source files, issue text or logs.
- Use isolated provider subaccounts and synthetic test identities in staging.
- Never log request bodies, phone addresses, raw media, signatures, access tokens or signed media URLs.
- A green process health check is not proof of provider, consent, media or carrier readiness.

## Startup checklist

1. Confirm PostgreSQL version and apply migrations in numeric order through `0005_tenant_ownership.sql`.
2. Verify database credentials are least-privilege and tenant migration is complete.
3. Inject hashed API-token configuration and verify tokens are sourced from the approved secret manager.
4. Configure canonical public HTTPS origin; do not derive it from arbitrary forwarded headers.
5. Keep the Twilio adapter disabled until its account preflight, consent IVR, address resolver and reconciliation tests pass.
6. Verify logs redact request and provider data; verify no raw audio is retained in CI.
7. Confirm budget limits and call/number usage alerts before enabling any provider account.

## Incident response

| Signal | Immediate action | Evidence to preserve |
|---|---|---|
| Authentication spike / token leak | Disable affected token digest, rotate from secret manager, block ingress if needed | Timestamp, tenant ID, route, status counts; never token values |
| Cross-tenant access suspicion | Disable session API writes; preserve database audit; investigate tenant predicates | Session opaque IDs and sanitized query/audit metadata |
| Invalid webhook signature burst | Reject all invalid requests; do not decode or persist them | Provider account alias, timestamp, request digest, status only |
| Outbox lease backlog | Pause provider dispatch; inspect stable error codes and lease age | Command IDs, error codes, attempts, timestamps |
| Unknown provider side-effect outcome | Do not blindly retry; reconcile provider state first | Internal command/session IDs and provider resource IDs only |
| Consent mismatch | Stop new recording joins; close the session through a verified provider operation | Policy version, participant opaque refs, event IDs and digest references |
| Media validation failure | Quarantine metadata; do not publish or serve the artifact | Sanitized format, size, validation code and digest |
| Deletion failure | Keep tombstone and retry; do not report deletion complete | Internal object/provider IDs, attempt count, error code |

## Recovery and rollback

- API-only rollback: disable ingress or roll back to the previous tested image; preserve PostgreSQL data and migration history.
- Database restore: restore into an isolated instance first, verify tenant isolation and consent evidence, then authorize cutover.
- Outbox recovery: expired leases may be reclaimed by the repository, but provider operations must reconcile before retry.
- Do not delete provider resources or object data manually without recording the operation in the audit process.
- If media deletion cannot be confirmed across all copies, report it as pending/failed, not complete.

## Readiness gate

Before staging/production approval, add executable health/readiness checks, dashboards and alerts for API errors, database pool saturation, outbox age/dead letters, webhook signature failures, provider reconciliation unknowns, media validation failures and deletion backlog. Define owner, SLO, escalation and rollback trigger for each. This document alone does not mean monitoring or deployment exists.
