# Execution Decisions

These are conservative, reversible execution defaults for the 2026-11-23 engineering session. They do not override accepted ADRs or grant production authority.

## D-EXEC-001 — Keep release blocked
**Decision:** Keep release status BLOCKED until repository governance, real provider acceptance, physical-device/carrier evidence, AWS staging evidence and jurisdiction-specific legal/privacy approval are all present.  
**Reason:** CI, simulator behavior and source review cannot establish those external facts.  
**Revisit:** Only with independently reviewable evidence for each gate.

## D-EXEC-002 — Do not apply privileged or paid operations
**Decision:** Prepare scripts, payloads, validation and plans only. Do not mutate Rulesets through an unverified path, create AWS resources, incur Twilio charges, or deploy production/staging resources without explicit authorization.  
**Reason:** The connected GitHub API surface provides ruleset reads but no supported ruleset write action; AWS/Twilio account authority and budget are not established.  
**Revisit:** After a human administrator/operator executes the reviewed action and the resulting state is read back.

## D-EXEC-003 — Preserve pathway distinctions
**Decision:** Treat native SIM-call merge, app-owned Twilio Conference, imported audio and app-owned VoIP as separate product pathways. Never use one pathway's tests to claim another pathway's capability.  
**Reason:** The current Twilio Conference is app-owned outbound calling and does not prove access to native Phone.app audio.  
**Revisit:** Only with exact physical-device and provider evidence.

## D-EXEC-004 — Evidence tiers remain explicit
**Decision:** Label source review, unit/integration, simulator, physical-device, carrier and live-provider evidence separately. Never infer exactly-once remote execution from database idempotency.  
**Reason:** Provider side effects and physical carrier topology are external systems.  
**Revisit:** Per capability, with evidence attached to the exact commit/configuration.


## D-EXEC-005 — Use single-command outbox batches by default
**Decision:** Default the production worker to `WORKER_BATCH_SIZE=1` while each claimed command has a 60-second lease and dispatch is sequential. Emit sanitized cycle duration with aggregate counts.  
**Reason:** A large claimed batch can spend part of each later command's lease waiting for earlier provider operations.  
**Limit:** This reduces lease starvation but does not implement lease renewal or exactly-once remote execution. Increase batch size only after a measured worst-case bound with margin or lease renewal is proven.

## D-EXEC-006 — Preserve audit trail after reverted mainline mistakes
**Decision:** Do not force-push or rewrite main to remove the temporary add/revert commits created during this session.  
**Reason:** The current main tree compares equal to the original baseline (zero changed files); the history retains the add/revert audit trail.  
**Follow-up:** All further work remains on task branches; verify the branch argument before every GitHub contents write.


## D-EXEC-007 — Do not merge while live main governance is incomplete
**Decision:** Keep the nine execution PRs open and unmerged until the current main Ruleset GET confirms the intended PR review, required status checks, linear history and conversation-resolution controls.  
**Observed state:** Ruleset 27591151 is active but currently exposes only `deletion` and `non_fast_forward`. The prepared JSON and passing CI do not change this live state.  
**Reason:** The user requires merge only after real CI evidence and Ruleset compliance; treating a prepared payload as an applied ruleset would be false evidence.  
**Revisit:** After an authorized administrator applies the reviewed payload and the live GET read-back verifies every intended rule and required check identity.


## D-EXEC-008 — Governance verified; merge only on exact-head evidence

**Decision:** The prior D-EXEC-007 hold is superseded. The live Ruleset 27591151 read-back now verifies active main protection, no bypass actors, required PR/thread-resolution controls, linear history, and all eight strict required status checks. Merge each PR only after its updated exact head passes every required check and has no unresolved review threads or merge conflicts.

**Evidence:** PR #79 was squash-merged to main as `c2d3b23ccdb84aec8585b3a296b05eec3c241524`; the live Ruleset was read back after the change. PR branches #78 and #80–#87 were updated to include that main commit and new exact-head CI was triggered.

**Limits:** This does not authorize AWS apply/deploy, paid Twilio traffic, physical SIM testing, production release, or legal/customer claims. Those remain independently blocked until external evidence and approvals exist.


## D-EXEC-009 — Treat retention deletion as fenced, at-least-once external work

**Decision:** Retention deletion claims are per asset, committed before network calls, and fenced by a random claim token plus a five-minute lease. Persist Twilio and object-storage completion independently; retry only the unfinished stage and finalize only while the current token and unexpired lease still match.

**Reason:** A worker can crash after an external delete succeeds but before the database records it. Twilio DELETE and S3 DeleteObject are retried as idempotent operations; a provider 404 is treated as already deleted. The database fence prevents an expired worker from finalizing another worker's claim, but cannot cancel an external request already in flight.

**Limit:** This is at-least-once execution with idempotent retries, not exactly-once remote execution. No lease renewal or live Twilio/S3 acceptance is established by CI.

## D-EXEC-010 — Emit sanitized retention telemetry; keep alerting as a separate gate

**Decision:** Retention cycle logs include only processed ingestion count, deleted asset count, duration and exception class. Retry events include only a fixed stage label and exception class. Never log exception messages, provider identifiers, object keys, URLs, phone numbers, claim tokens or audio.

**Reason:** Silent worker failures and invisible durable retries are operationally unsafe; identifiers and exception messages may contain sensitive provider data.

**Limit:** Logs are not alerts. CloudWatch metric filters, alarms, notification routing and an exercised incident response remain unprovisioned and must be validated in AWS staging before operational acceptance.

## D-EXEC-011 — Refresh stale PR branches after every mainline merge

**Decision:** Recreate small documentation PRs from the latest main when their base becomes stale; do not bypass required checks or merge stale heads. Keep the superseded branch until its replacement is merged, then remove it only after confirming it is no longer needed.

**Reason:** Main protection requires exact-head CI and a fresh base. A passing run on an older commit does not certify a replacement branch or newer mainline state.
