# Backend and companion threat model

**Review status:** engineering threat-model pass updated 2026-11-20. This is not a penetration test, legal opinion, DPIA or release approval. The Twilio code path has not been exercised against a live account and AWS Terraform has not been applied.

## Scope and trust boundaries

In scope: iOS imported audio and local catalog; authenticated session/media API; PostgreSQL sessions, consent evidence, event receipts, outbox, provider-resource mappings and audit tables; Twilio signed webhook ingress and REST calls; participant-address vault; media retrieval, S3/KMS storage and retention; AWS ECS/RDS/ALB/IAM/Secrets Manager deployment artifacts.

Trust boundaries:
1. iOS process ↔ imported Files/iCloud/document-provider URLs.
2. untrusted client ↔ authenticated API ↔ tenant-scoped PostgreSQL.
3. Twilio ↔ public HTTPS webhook ingress ↔ signature verifier ↔ event processor.
4. worker ↔ Twilio REST APIs and secret manager.
5. Twilio recording endpoint ↔ bounded retrieval worker ↔ KMS-encrypted S3.
6. API client ↔ short-lived presigned media URL.
7. operator ↔ production database, logs, backups, cloud IAM and support tooling.

## Assets and security objectives

| Asset | Security objective |
|---|---|
| Raw recordings and derived media | Confidentiality, integrity, explicit user control, bounded retention |
| Participant phone addresses | Confidentiality; decrypt only for authorized provider side effects |
| API bearer credentials and provider secrets | Confidentiality, rotation, least privilege |
| Session/tenant ownership | No cross-tenant read, mutation, export or deletion |
| Consent evidence | Authenticity, provenance, immutability and participant coverage |
| Provider webhook events | Authenticity, replay resistance, account binding and ordering safety |
| Outbox commands and provider resource mappings | Integrity, no PII, safe reconciliation after uncertain side effects |
| Media metadata and download grants | Tenant-scoped access, integrity, short TTL and audit |
| Operational logs and backups | No call content or credentials; controlled access and deletion lifecycle |

## Threat register

| ID | Threat / abuse case | Required control | Current implementation / residual |
|---|---|---|---|
| T01 | Cross-tenant session enumeration or mutation | Tenant-scoped SQL predicates, opaque IDs, no existence disclosure | Tenant-scoped session reads/cancel and address/media access queries; PostgreSQL integration tests |
| T02 | Bearer token theft/replay | High-entropy tokens, digest-only configuration, TLS, rotation, rate limiting, audit | SHA-256 token digest lookup and no-store responses; TLS is in AWS ALB Terraform, but no cloud is deployed; rate limiting and rotation automation remain open |
| T03 | Malicious participant reference or phone-number injection | Accept only opaque bounded references; resolve addresses in protected vault; never persist addresses in outbox/logs | AES-256-GCM tenant-scoped address vault, E.164 validation, authenticated provisioning/deletion API and metadata-only audit table |
| T04 | Forged/replayed webhook changes consent or starts recording | Provider-native signature verification over exact raw request; event ID uniqueness; payload digest; account binding; timestamp policy | Twilio signed ASGI ingress, exact canonical URL/body, duplicate field rejection, Account SID binding, account-scoped resolver and durable event deduplication; no live provider replay test or ingress rate limit |
| T05 | Consent bypass by initiator or merged carrier leg | Consent from every expected human before recording-enabled join; fail closed on unknown identity/topology | DTMF 1 consent, empty/other digit/terminal call decline, consent evidence, cancellation of other calls and session guard; disclosure requires counsel approval; native SIM-party identity and carrier merge remain unproven |
| T06 | SSRF via callback-controlled media URL | Never fetch arbitrary URL; construct provider resource URL from validated provider IDs and fixed API origin | Fixed Twilio API host, validated Recording SID and RequestedChannels=2; callback-supplied media URLs are ignored |
| T07 | Signed media URL or phone number leaks into logs/outbox | Strict payload schema, redaction, no raw provider response logging | Outbox carries opaque participant refs; address API does not echo phone number; webhook events store digest/opaque refs; media download URL is short-lived and not logged; production log review remains open |
| T08 | Duplicate worker delivery creates duplicate conference/call | Lease token, idempotency key, provider reconciliation before retry | Transactional outbox, supervised worker, separate immutable consent-call and Conference-leg mappings; ambiguous unmapped Call.create returns UNKNOWN and is not blindly retried; live provider behavior unverified |
| T09 | Local file exposed while device locked or included in backups | Complete file protection, app-private paths, backup exclusion, explicit export | Complete file protection and directory backup exclusion implemented; physical lock/reboot tests remain |
| T10 | Low storage or process death corrupts catalog/media | Preflight capacity, staging, atomic catalog, known-good backup, foreground reconciliation | Low-space preflight, finite background task lease, partial-file cleanup and catalog recovery implemented; physical kill/low-space matrix remains |
| T11 | Malicious/corrupt media exhausts memory/CPU or parser | Size/duration limits, bounded reads, container/chunk validation, decoder limits | Bounded streaming download, 500 MiB limit, WAV chunk/format validation, stereo PCM16 analysis; malformed/oversized media is persisted as rejected and retained for coordinated deletion |
| T12 | Operator or backup access exposes recordings | Least privilege, encryption, access audit, backup lifecycle and tested deletion | AWS Terraform defines private bucket, public-access block, KMS encryption, task-role object permissions and lifecycle expiry; no bucket/IAM/KMS resource has been deployed |
| T13 | Retention deletion succeeds in one system but not another | Durable tombstones, retries, reconciliation and observable terminal state | Retention worker tracks Twilio and S3 deletion separately and sets deleted_at only after both succeed; live provider/S3 deletion acceptance and backlog alerts remain |
| T14 | Unauthorized media download or long-lived URL sharing | Tenant authorization, verified-only access, minimal URL lifetime, access audit | GET media endpoint issues 120-second presigned URL only for verified, undeleted assets and records media_access_audit; cloud IAM and live S3 policy not applied |
| T15 | Decline/cancel races with outbound consent call creation | Terminal state guard, pending-command cancellation and provider leg closure | Pending consent requests are dead-lettered, worker checks session state before/after Calls.create, and cancellation commands close mapped active consent calls; live race acceptance remains |

## Abuse-case test requirements

- Tenant A cannot read, cancel, provision or download Tenant B's session/media.
- Missing, malformed, expired or unknown credentials fail closed.
- Oversized/malformed JSON and participant reference injection are rejected before persistence.
- Cancellation does not claim to stop an active Conference; it closes consent calls only while the session is in the pre-join consent state.
- Forged webhook signatures are rejected before event decoding or persistence.
- Replayed event IDs do not repeat consent transitions or provider commands.
- Outbox retries reconcile provider state before any non-idempotent side effect.
- Provider media retrieval never follows a callback-supplied arbitrary URL.
- Corrupt/truncated/oversized media is rejected before object persistence and remains eligible for provider-side retention deletion.
- Download URL issuance requires tenant ownership and verified media; URL lifetime is 120 seconds and issuance is audit-recorded.
- Locked-device and reboot tests verify media is unavailable until first unlock.
- Deletion tests verify every provider and product copy, not only the catalog row.

## Release-blocking residuals

1. Deploy the API behind the configured HTTPS ALB; add rate limits, token rotation, ingress abuse controls and verified log redaction.
2. Run a real Twilio account test for consent, call creation, Conference callback ordering, RequestedChannels=2 recording, download, verification and provider deletion.
3. Validate native SIM-call merge and physical audio routes on exact iPhone/carrier/SIM/accessory tuples before making any SIM-recording claim.
4. Apply AWS Terraform only after VPC/subnet, ACM/DNS, Secrets Manager and budget approval; verify IAM/KMS/S3 policies and ECS rollback.
5. Add dashboards/alerts for outbox age/dead letters, webhook failures, unknown reconciliation, media verification failures, deletion backlog, API 5xx and spend.
6. Complete independent security review, penetration tests, backup/restore, jurisdiction-specific legal/privacy review and App Store review.

**Decision:** several high-risk software boundaries now have implementation and automated test coverage, but the system is not production-secure or release-approved. Keep TWILIO_ENABLED=false until live provider, legal, physical and cloud acceptance gates are closed with evidence.
