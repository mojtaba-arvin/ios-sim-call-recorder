# Privacy and Security Release Checklist

**Review date:** 2026-11-23  
**Status:** engineering checklist prepared; not a penetration test, DPIA, legal opinion, independent security audit or release approval.  
**Source:** [Threat model](threat-model.md), [operations runbook](../operations/runbook.md), [counsel brief](../legal/counsel-brief.md).

## Status vocabulary

- **IMPLEMENTED — CODE:** source and automated tests exist; deployment and independent verification may still be open.
- **CI VERIFIED:** the named check passed on an exact commit; no broader claim is implied.
- **BLOCKED-ACCESS:** account, deployment, role, credential or administrative evidence is missing.
- **BLOCKED-HARDWARE:** physical iPhone/SIM/accessory evidence is missing.
- **BLOCKED-EXTERNAL:** counsel, customer, provider or independent reviewer evidence is missing.
- **NOT VERIFIED:** not independently exercised or observed.

## Release checklist

| ID | Control | Current evidence / implementation | Release status | Required closure evidence |
|---|---|---|---|---|
| P01 | No private Phone.app audio interception or private APIs | README and architecture boundary; import-only companion | IMPLEMENTED — CODE | Reconfirm marketing and App Store copy |
| P02 | Explicit participant consent before recording-enabled Conference join | DTMF 1 gate, consent evidence and pre-join recording-from-start flow | IMPLEMENTED — CODE | Live Twilio staging run with every participant's consent |
| P03 | Jurisdiction-specific notice and legal basis | Counsel brief and configurable disclosure input | BLOCKED-EXTERNAL | Written counsel approval for exact jurisdiction, flow, wording, retention and deletion |
| P04 | Tenant isolation for session, address and media operations | Tenant-scoped API/database predicates and PostgreSQL tests | CI VERIFIED — commit-scoped; verify the exact current head in the execution record | Independent authorization review and deployed integration evidence |
| P05 | Participant address minimization | Opaque refs in outbox; encrypted tenant-scoped AES-GCM vault | IMPLEMENTED — CODE | Verify deployed key custody, rotation and access logs |
| P06 | Provider webhook authenticity | Official Twilio signature validator, canonical URL/raw form and account binding | IMPLEMENTED — CODE | Real provider callback verification and replay test |
| P07 | Webhook replay and duplicate handling | Durable event deduplication and account-scoped rate limits | CI VERIFIED — commit-scoped; verify the exact current head in the execution record | Live callback replay and ordering evidence |
| P08 | Outbox side-effect safety | Transactional outbox, lease dispatcher, resource reconciliation and UNKNOWN state | IMPLEMENTED — CODE | Crash-window tests against staging provider; no exactly-once claim |
| P09 | API idempotency | Tenant-scoped key, request digest, unique constraint and expiry cleanup | CI VERIFIED — commit-scoped; verify the exact current head in the execution record | Deployed API retry/concurrency acceptance |
| P10 | Rate limiting | PostgreSQL tenant and provider-account token buckets; ALB/WAF source-IP rule in Terraform | IMPLEMENTED — CODE | AWS deployment and observed threshold tuning |
| P11 | Media validation | Bounded retrieval, WAV/container checks, stereo activity verification | CI VERIFIED — commit-scoped; verify the exact current head in the execution record | Real recording artifact independently inspected |
| P12 | Media confidentiality at rest | KMS/S3 encryption and private bucket policy in Terraform | IMPLEMENTED — CODE | AWS KMS/S3/IAM policy read-back after approved apply |
| P13 | Media access | Tenant ownership, verified media requirement, 120-second presigned URL and audit record | IMPLEMENTED — CODE | Deployed IAM/access audit verification |
| P14 | Provider and object deletion | Coordinated Twilio/S3 deletion state machine and retention worker | IMPLEMENTED — CODE | Real provider + S3 deletion evidence and backlog monitoring |
| P15 | Local iOS file protection | Complete file protection, app-private storage and backup exclusion | IMPLEMENTED — CODE | Locked-device, reboot-before-first-unlock and backup tests on physical iPhone |
| P16 | Catalog and import integrity | Atomic catalog writes, validated backup, streaming SHA-256 and fail-closed recovery | CI VERIFIED — commit-scoped; verify the exact current head in the execution record | Physical storage pressure/process termination acceptance |
| P17 | Log and telemetry minimization | Sanitized errors and metadata-only audit design | IMPLEMENTED — CODE | Review deployed logs, traces, crash reports and support tooling |
| P18 | Secrets and least privilege | Secrets Manager and ECS task roles defined in Terraform | BLOCKED-ACCESS | AWS IAM policy read-back, secret rotation and OIDC trust review |
| P19 | Network and edge security | HTTPS ALB, private RDS and WAF in Terraform | BLOCKED-ACCESS | AWS deployment, TLS/DNS, WAF metrics and external scan |
| P20 | Backups and recovery | Database backup and media lifecycle settings in Terraform | NOT VERIFIED | Restore drill, RPO/RTO evidence and deletion lifecycle review |
| P21 | Supply-chain / CI hardening | Pinned action SHAs, least-privilege workflow permissions and Release Preflight | CI VERIFIED — commit-scoped; verify the exact current head in the execution record | Dependency/SBOM review, secret scan and exact-head CI |
| P22 | Independent security assessment | Threat model exists | BLOCKED-EXTERNAL | Independent code review, penetration test and remediation verification |
| P23 | Privacy impact / data residency | Data-flow and counsel documents exist | BLOCKED-EXTERNAL | Written DPIA/privacy review, subprocessors and cross-border transfer assessment |
| P24 | Incident response and support | Operations runbook exists | NOT VERIFIED | Named on-call owner, escalation drill, breach response and customer communication test |

## Required test evidence

- Tenant A cannot enumerate, read, mutate, export or delete Tenant B's sessions, participant addresses or media.
- Forged, malformed, replayed and wrong-account provider callbacks fail closed before domain side effects.
- Outbox crash windows reconcile uncertain provider outcomes without blind duplicate calls.
- Declined/unavailable participants never result in recording-enabled joins.
- Corrupt, truncated, oversized, mono or one-sided media is rejected/degraded; neither provider metadata nor a URL alone marks media verified.
- Deletion is independently confirmed in every provider/object store; catalog deletion alone is insufficient.
- Locked-device and reboot-before-first-unlock behavior is tested on physical hardware.
- Backup restore and retention/deletion interactions are exercised.
- Production logs, traces, metrics and crash reports are reviewed for phone numbers, credentials, media URLs, raw payloads and call content.

## Current release decision

**BLOCKED.** Release Preflight results are commit-scoped and must be checked against the exact current PR or main SHA in the execution record. Historical baseline runs do not close any external status above. Keep `TWILIO_ENABLED=false`; do not deploy AWS, initiate paid PSTN calls or claim legal/security approval until the corresponding rows have independently reviewed evidence.
