# Backend and companion threat model

**Review status:** engineering threat-model pass completed 2026-11-20. This is not a penetration test, legal opinion, DPIA or release approval. Revisit when provider ingress, address vault, media storage and deployment are introduced.

## Scope and trust boundaries

In scope: iOS imported audio and local catalog; authenticated session API component; PostgreSQL sessions, consent evidence, event receipts and outbox; future provider webhook, participant-address and media boundaries.

Trust boundaries:
1. iOS process ↔ imported Files/iCloud/document-provider URLs.
2. untrusted client ↔ authenticated API ↔ tenant-scoped PostgreSQL.
3. provider ↔ public webhook ingress ↔ normalized event processor.
4. worker ↔ provider REST APIs and secret manager.
5. provider media endpoint ↔ retrieval worker ↔ tenant object storage.
6. operator ↔ production database, logs, backups and support tooling.

## Assets and security objectives

| Asset | Security objective |
|---|---|
| Raw recordings and derived media | Confidentiality, integrity, explicit user control, bounded retention |
| Participant phone addresses | Confidentiality; resolve only for authorized provider side effects |
| API bearer credentials and provider secrets | Confidentiality, rotation, least privilege |
| Session/tenant ownership | No cross-tenant read, mutation, export or deletion |
| Consent evidence | Authenticity, provenance, immutability and participant coverage |
| Provider webhook events | Authenticity, replay resistance, idempotency and ordering safety |
| Outbox commands and provider resource mappings | Integrity, no PII, safe reconciliation after uncertain side effects |
| Catalog and retention metadata | Integrity, recovery without orphaning user media |
| Operational logs and backups | No call content or credentials; controlled access and deletion lifecycle |

## Threat register

| ID | Threat / abuse case | Required control | Current implementation / residual |
|---|---|---|---|
| T01 | Cross-tenant session enumeration or mutation | Tenant-scoped SQL predicates, opaque IDs, no existence disclosure | Tenant column, scoped reads and cancellation implemented; PostgreSQL integration tests added |
| T02 | Bearer token theft/replay | High-entropy tokens, digest-only configuration, TLS, rotation, rate limiting, audit | SHA-256 digest lookup and no-store responses implemented; TLS, rate limiting and rotation automation remain deployment tasks |
| T03 | Malicious participant reference or phone-number injection | Accept only opaque bounded references; resolve addresses in a protected vault; never persist addresses in outbox/logs | API accepts opaque refs and domain validates them; secure address vault/resolver remains unimplemented |
| T04 | Forged/replayed webhook changes consent or starts recording | Provider-native signature verification over exact raw request; event ID uniqueness; payload digest; account binding; timestamp/replay policy | Signature verifier and durable event deduplication exist; HTTP ingress/decoder and provider-account binding remain open |
| T05 | Consent bypass by initiating user or merged carrier leg | Consent from every expected human before recording-enabled join; fail closed on unknown identity/topology | Domain and outbox preflight gate implemented; merged SIM-party identity and lawful consent path unproven |
| T06 | SSRF via callback-controlled media URL | Never fetch arbitrary URL; construct provider resource URL from validated provider IDs and fixed API origin | No media retrieval implementation yet; must be an explicit adapter invariant |
| T07 | Signed media URL or phone number leaks into logs/outbox | Strict payload schema, redaction, no raw provider response logging | Outbox rejects sensitive keys; production logging policy and webhook redaction still require verification |
| T08 | Duplicate worker delivery creates duplicate conference/call | Lease token, idempotency key, provider reconciliation before retry | Transactional outbox/lease dispatcher implemented; no live adapter, so provider-side reconciliation unproven |
| T09 | Local file exposed while device locked or included in backups | Complete file protection, app-private paths, backup exclusion, explicit export | Production media/catalog protection and directory backup exclusion implemented; physical lock/reboot test remains |
| T10 | Low storage or process death corrupts catalog/media | Preflight capacity, staging, atomic catalog, known-good backup, foreground reconciliation | Implemented with deterministic low-space test and existing catalog recovery tests; physical kill/low-space matrix remains |
| T11 | Malicious/corrupt media exhausts memory/CPU or parser | Size/duration limits, bounded reads, container/chunk validation, decoder limits | iOS import and backend WAV structural validator cover bounded supported inputs; other backend media codecs not supported |
| T12 | Operator or backup access exposes recordings | Least privilege, encryption, access audit, backup lifecycle and tested deletion | KMS-encrypted S3 adapter with tenant-derived opaque keys implemented; bucket policy, IAM/KMS grants, versioning, access audit and backup lifecycle remain deployment tasks |
| T13 | Retention deletion succeeds in one system but not another | Durable tombstones, retries, reconciliation and observable terminal state | Local retention exists; provider/object-store deletion reconciliation remains open |

## Abuse-case test requirements

- Tenant A cannot read, cancel or infer Tenant B's session.
- Missing, malformed, expired or unknown credentials fail closed.
- Oversized/malformed JSON and participant reference injection are rejected before persistence.
- Cancellation never claims to stop a provider call; active sessions require a provider close operation.
- Forged webhook signatures are rejected before event decoding or persistence.
- Replayed event IDs do not repeat consent transitions or provider commands.
- Outbox retries reconcile provider state before any non-idempotent side effect.
- Provider media retrieval never follows a callback-supplied arbitrary URL.
- Corrupt/truncated media is rejected before object persistence.
- Locked-device and reboot tests verify media is unavailable until first unlock.
- Deletion tests verify every provider and product copy, not only the catalog row.

## Release-blocking residuals

1. Deploy the API behind TLS with rate limiting, token rotation, request limits and audited secret injection.
2. Implement a secure participant-address vault/resolver with tenant-scoped authorization and encryption at rest.
3. Implement public webhook ingress with exact URL reconstruction, signature validation, replay policy, account ownership and idempotent event decoding.
4. Implement provider adapter and supervised worker with reconciliation.
5. Implement SSRF-safe media retrieval, encrypted tenant object storage and deletion reconciliation.
6. Complete independent security review, penetration tests, backup/restore and jurisdiction-specific legal/privacy review.

**Decision:** current API and local companion controls reduce several known risks, but the system is not production-secure or release-approved. Do not expose the API publicly or enable live recording until the residual controls are implemented and tested.
