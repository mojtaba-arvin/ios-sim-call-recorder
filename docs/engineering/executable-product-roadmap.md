# Executable Product Roadmap

**Snapshot:** 2026-11-19  
**Purpose:** turn the repository's research and implementation into a sequenced, evidence-gated delivery plan. This is a living execution document, not a claim that hardware, carrier or production work has passed.

## Product boundary and release definition

The product has two distinct modes and they must not be conflated:

1. **Native-call companion:** the user obtains a recording through an OS/carrier/accessory-supported route and explicitly imports it. The app manages, validates, plays, exports and deletes the file. It does not intercept Phone.app audio.
2. **App-owned/provider bridge:** the backend coordinates provider call legs and records a conference after all required participants have received disclosure and affirmatively consented. This does not prove that a carrier can merge an existing SIM call into the bridge.

A release may claim support only for exact device, OS build, region, carrier/plan, SIM/network, accessory and call-topology tuples that pass the acceptance protocol. No universal carrier, device or two-way-capture claim is permitted.

## Current baseline

### Implemented in main (software evidence)

- Swift recording core and cancellation/resource-lifecycle behavior.
- SwiftUI companion shell with user-mediated file import, app-private storage, local catalog, playback, seeking, system share/export, opt-in retention and catalog recovery.
- WAV RIFF/chunk boundary checks and bounded AVFoundation decode validation are proposed in the current import-hardening PR; merge only after its fresh mainline CI passes.
- Audio quality analyzer and deterministic WAV fixtures.
- Provider-neutral bridge state machine, consent gate, signed-webhook verification boundary, PostgreSQL persistence, transactional outbox, lease-based dispatcher, reconciliation contract and immutable provider-resource mappings.
- CI workflows for Swift, iOS Simulator, audio analysis, backend/PostgreSQL and repository policy.

### Not implemented / not proven

- A deployable authenticated HTTP service and public webhook ingress.
- A concrete Twilio/Telnyx provider adapter with safe address resolution, provider-account preflight and live account validation.
- Production outbox worker process, secrets management, infrastructure, media ingestion/object storage, audio verification and retention/deletion jobs.
- Physical iPhone/carrier/accessory evidence for two-way intelligible capture.
- Legal review and App Store approval for each launch market.
- Production deployment or end-to-end paid provider call.

## Delivery sequence

### M0 — Stabilize the integration baseline

- [ ] Merge the import payload hardening only after fresh Swift, iOS Simulator and backend checks pass on its mainline PR head.
- [ ] Resolve or supersede the stale stacked import PR; leave one canonical implementation path.
- [ ] Review and merge the product README, evidence templates and provider session contract after documentation checks.
- [ ] Consolidate the governance/agent-tooling PRs without reverting current CI path filters, permissions, action pins or cache improvements.
- [ ] Verify default-branch checks and ruleset behavior; document any settings that the repository integration cannot change.
- [ ] Publish one dependency map and close obsolete/orphan branches only after confirming their changes are represented.

**Exit gate:** clean mainline; all required checks green; no duplicate stacked PRs; one source of truth for project scope, evidence and release gates.

### M1 — Finish the native-call companion

- [x] User-mediated import and private local storage.
- [x] Local playback, seeking, interruptions/output-route handling and user-initiated export.
- [x] Opt-in retention, backup catalog recovery and fail-closed storage behavior.
- [ ] Complete import adversarial cases on the current mainline and keep format-specific claims bounded by decoder evidence.
- [ ] Run VoiceOver and Dynamic Type review on physical devices; record OS/device tuples.
- [ ] Add app lifecycle/background/low-storage recovery checks and verify file protection after device lock/reboot.
- [ ] Add release signing, privacy manifest/permission review, app icon/metadata and a reproducible archive build.

**Exit gate:** app builds from a clean checkout; import/play/export/delete/retention survive relaunch and interruption; accessibility and privacy review evidence attached. This mode remains a companion/import app, not a native Phone-call recorder.

### M2 — Prove a real capture pathway

Run the tracks in parallel; do not select a pathway from documentation alone.

- [ ] **Apple native recording:** test availability by OS, physical region and language; test user export/import and artifact integrity. Do not assume Notes private APIs.
- [ ] **Carrier conference merge:** on consenting test SIMs, verify add-call/merge, hold, call waiting, interruption and hang-up behavior for inbound and outbound calls.
- [ ] **External HFP/wired accessory:** identify a specific accessory and signal path; prove both uplink and downlink are present in the saved artifact. Pairing or microphone access alone is not proof.
- [ ] **Acoustic fallback:** measure speakerphone plus independent recorder in controlled noise/distance conditions.
- [ ] For each positive tuple, repeat at least three calls and independently verify local and remote speech; record exact model, iOS build, region, carrier/plan, SIM, network, route, accessory firmware, consent and signal metrics.

**Exit gate:** at least one lawful repeatable pathway has three positive two-way samples on an explicitly named compatibility tuple. Otherwise ship only the companion/import capability and state that recording capture is not supported.

### M3 — Turn the backend foundation into a deployable service

- [ ] Define and implement authenticated session create/read/cancel endpoints, tenant authorization, idempotency and rate limits.
- [ ] Implement canonical public-origin configuration and trusted-proxy handling; reject arbitrary forwarded-host reconstruction.
- [ ] Implement Twilio webhook decoding after signature verification, account/resource ownership checks, event normalization, deduplication and out-of-order handling.
- [ ] Implement a provider address resolver keyed by opaque participant references. Resolve phone numbers only in memory from a protected vault; never place them in outbox rows, logs or ordinary audit payloads.
- [ ] Implement Twilio conference creation/join semantics using the documented TwiML/Participants flow; do not assume a Conference can be directly created through the Conference resource.
- [ ] Implement provider reconciliation for timeout-after-acceptance, duplicate participant labels, concurrent joins, stale resources and account mismatch. Unknown outcomes must defer, never blindly retry.
- [ ] Gate recording start on joined-participant completeness and durable affirmative consent evidence for every participant.
- [ ] Implement recording stop/finalization, callback reconciliation and provider-side deletion.
- [ ] Add a supervised worker entry point, graceful shutdown, bounded network timeouts shorter than leases, lease renewal strategy, health/readiness endpoints and structured redacted logs.
- [ ] Add migration runner, deployment configuration, secret injection/rotation, least-privilege database/provider credentials and backup/restore procedures.

**Exit gate:** deterministic mock/contract tests cover the full lifecycle and crash windows; staging preflight confirms provider account configuration; no real call or production credential is used in CI.

### M4 — Media ingestion and verification

- [ ] Fetch completed media server-side using authenticated provider APIs; never trust arbitrary callback URLs.
- [ ] Validate content type, byte limits, duration, container structure and full decodability before persistence.
- [ ] Store encrypted media in tenant-scoped object storage with opaque keys and short-lived authorized downloads.
- [ ] Verify channel semantics and analyze each channel independently (RMS/peak, silence, clipping, gaps, duration and sample rate).
- [ ] Require human or independently validated speech evidence for both directions; channel count or provider metadata alone is insufficient.
- [ ] Persist verification summary and provenance, not raw audio or transcript in logs.
- [ ] Implement provider-side and product-side retention/deletion reconciliation, including failed deletions and retryable tombstones.

**Exit gate:** synthetic integration tests plus consented staging recordings pass the complete media lifecycle; deletion is demonstrably complete across provider and product copies.

### M5 — Security, privacy and market readiness

- [ ] Threat-model tenant isolation, webhook forgery/replay, SSRF, signed media URL leakage, object authorization, credential rotation and outbox tampering.
- [ ] Review consent/disclosure wording and affirmative-consent capture for each launch jurisdiction.
- [ ] Complete data-protection impact assessment, lawful basis, data residency, retention defaults, user export/deletion and incident response.
- [ ] Review Apple App Store rules, privacy labels, background behavior, audio recording disclosure and all required permissions.
- [ ] Verify emergency-call exclusion and safe failure behavior; never silently record or bypass system disclosure.
- [ ] Run dependency, secret, static-analysis and backup/restore checks.

**Exit gate:** written legal/privacy/security approval for each market and release configuration. Engineering tests cannot substitute for this approval.

### M6 — Staging, production and controlled rollout

- [ ] Deploy a non-production environment with isolated provider subaccount, test numbers, synthetic data and budget/usage alerts.
- [ ] Run end-to-end staging scenarios with consenting participants; validate both audio directions and cleanup.
- [ ] Exercise worker crash/restart, webhook replay, provider timeout, database failover, object-store outage and deletion retry.
- [ ] Publish runbooks, dashboards, alerts, SLOs, support diagnostics and rollback procedures.
- [ ] Release to a small allowlisted compatibility cohort only after all gates pass.
- [ ] Expand support tuple-by-tuple using measured evidence; never infer support for untested carriers/regions/devices.

**Exit gate:** production readiness review, explicit account/usage authorization, tested rollback and a documented supported-configuration list.

## Non-negotiable engineering rules

- No native Phone.app audio interception claim; CallKit is not a native cellular-call capture API.
- No recording before every required participant has affirmatively consented.
- No phone numbers, tokens, signatures, media URLs, recordings or transcripts in outbox payloads or ordinary logs.
- No blind retry of uncertain provider side effects; reconciliation first.
- No provider credentials, paid calls or live numbers in CI. Use mocks and synthetic fixtures.
- No physical-device/carrier/hardware acceptance marked complete without attached, sanitized evidence.
- A workflow passing on a PR head is evidence only for that SHA and test environment.
- A task is Done only when implementation, tests, documentation, security implications and acceptance evidence are complete.

## Immediate next execution batch

1. Finish fresh CI and merge the import-hardening mainline PR.
2. Merge the README/evidence forms and bridge session contract after documentation integrity checks.
3. Resolve the governance/tooling PR stack without regressing the existing workflows.
4. Start M3 with the HTTP/session API and secure opaque-participant address resolver before provider side effects.
5. In parallel, prepare M2 physical-device test protocol and a consented test matrix; keep it blocked until devices/SIMs/accessories are available.
