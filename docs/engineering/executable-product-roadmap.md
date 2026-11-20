# Executable Product Roadmap

**Snapshot:** 2026-11-20  
**Purpose:** turn the repository's research and implementation into a sequenced, evidence-gated delivery plan. This is a living execution document, not a claim that hardware, carrier or production work has passed.

## Product boundary and release definition

The product has two distinct modes and they must not be conflated:

1. **Native-call companion:** the user obtains a recording through an OS/carrier/accessory-supported route and explicitly imports it. The app manages, validates, plays, exports and deletes the file. It does not intercept Phone.app audio.
2. **App-owned/provider bridge:** the backend coordinates provider call legs and records a conference after all required participants have received disclosure and affirmatively consented. This does not prove that a carrier can merge an existing SIM call into the bridge.

A release may claim support only for exact device, OS build, region, carrier/plan, SIM/network, accessory and call-topology tuples that pass the acceptance protocol. No universal carrier, device or two-way-capture claim is permitted.

## Current baseline

### Implemented in main (software evidence)

- Swift recording core and cancellation/resource-lifecycle behavior.
- VoiceOver status announcements, accessibility labels/identifiers and Dynamic Type-compatible system text styles; physical accessibility review remains open.
- Low-storage import preflight with a 64 MiB reserve, foreground catalog/staging recovery and explicit complete file protection for production media/catalog files.
- Bundled PrivacyInfo.xcprivacy declaring app-owned UserDefaults (CA92.1) and disk-space access (E174.1); signing and full App Store review remain open.
- SwiftUI companion shell with user-mediated file import, app-private storage, local catalog, playback, seeking, system share/export, opt-in retention and catalog recovery.
- WAV RIFF/chunk boundary checks and bounded AVFoundation decode validation are merged in PR #40; software import validation is complete for the covered formats and fixtures.
- Audio quality analyzer and deterministic WAV fixtures.
- Provider-neutral bridge state machine, consent gate, signed-webhook verification boundary, PostgreSQL persistence, transactional outbox, lease-based dispatcher, reconciliation contract and immutable provider-resource mappings.
- Authenticated tenant-scoped ASGI session create/read/cancel component, PostgreSQL tenant ownership, liveness/readiness endpoints and ordered migration runner.
- Signed Twilio webhook ASGI transport adapter (injected event decoder), graceful outbox worker loop, encrypted tenant-scoped participant-address vault and local staging container/Compose scaffold.
- Bounded server-side WAV structural validation with digest, format, channel-count, sample-rate, duration and chunk-boundary checks.
- CI workflows for Swift, iOS Simulator, audio analysis, backend/PostgreSQL and repository policy.

### Not implemented / not proven

- Production ASGI deployment with TLS ingress, rate limiting, durable API idempotency and automated credential rotation; the current ASGI app component and local staging scaffold are not a public service.
- A concrete Twilio/Telnyx command adapter, production webhook event decoder/account preflight and verified live account configuration.
- Production worker supervision/lease renewal and provider-backed remote cancellation; the current worker is a graceful polling loop only.
- Provider media retrieval, encrypted object storage, two-sided/channel identity verification and provider/product deletion reconciliation; current backend media validation is WAV-only structural validation.
- Physical iPhone/carrier/accessory evidence for two-way intelligible capture.
- Legal review and App Store approval for each launch market.
- Production deployment or end-to-end paid provider call.

## Product validation gate (before production-scale investment)

The detailed evidence, customer-discovery protocol, segment hypotheses, competitor/substitute analysis, commercial gates and go/no-go criteria live in [Product validation](../research/product-validation.md).

- [x] Complete current-snapshot platform and pathway desk research; keep every unsupported claim classified as a hypothesis.
- [ ] Select one launch jurisdiction and one initial customer segment; do not infer either from repository or account metadata.
- [ ] Complete problem interviews and prototype tests for that segment.
- [ ] Obtain paid-pilot / procurement evidence and conservative unit economics.
- [ ] Complete jurisdiction-specific legal/privacy review of the actual call flow.
- [ ] Pass a lawful physical capture pathway gate before claiming native SIM-call recording.

**Exit gate:** problem, solution, commercial, legal/trust and physical-feasibility gates are independently evidenced. A desk-research report or green CI is not product-market validation.

## Delivery sequence

### M0 — Stabilize the integration baseline

- [x] Merge the import payload hardening; PR #40 is on main and its simulator/core checks passed.
- [x] Resolve the stale stacked import PR; PR #32 was closed after the clean mainline implementation in PR #40.
- [x] Consolidate governance/agent-tooling in PR #42 without reverting CI path filters, permissions, action pins or cache improvements.
- [ ] Verify default-branch required-check behavior and strengthen the `protect main` ruleset; current ruleset only enforces deletion/non-fast-forward, while legacy branch protection is disabled.
- [ ] Publish one dependency map and prune superseded branches; five obsolete branches are identified, but branch deletion is not available through the connected GitHub operations.

**Exit gate:** clean mainline; all required checks green; no duplicate stacked PRs; one source of truth for project scope, evidence and release gates.

### M1 — Finish the native-call companion

- [x] User-mediated import and private local storage.
- [x] Local playback, seeking, interruptions/output-route handling and user-initiated export.
- [x] Opt-in retention, backup catalog recovery and fail-closed storage behavior.
- [x] Complete import adversarial cases on the current mainline with PR #40; keep format-specific claims bounded by decoder evidence.
- [x] Add VoiceOver status announcements, accessible status/progress semantics and Dynamic Type-compatible system typography; [ ] complete physical VoiceOver/Switch Control/Dynamic Type review on device.
- [x] Add low-storage preflight and foreground recovery of interrupted imports/catalog/staging; [ ] execute physical low-storage/process-kill scenarios.
- [x] Apply complete file protection to production media and catalog files and exclude app storage from backups; [ ] verify lock/reboot/first-unlock behavior on a physical device.
- [x] Bundle PrivacyInfo.xcprivacy with the UserDefaults and DiskSpace required-reason declarations; [ ] complete transitive SDK/privacy-label review.
- [ ] Configure Apple Developer Team, distribution signing identity/provisioning and reproducible signed Release archive; credentials are not available in this repository workflow.

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

- [x] Implement authenticated tenant-scoped ASGI session create/read/cancel component and PostgreSQL tenant ownership; [ ] add durable API idempotency, rate limits and production token rotation.
- [ ] Implement canonical public-origin configuration and trusted-proxy handling; reject arbitrary forwarded-host reconstruction.
- [x] Implement bounded signed-webhook ASGI transport that preserves raw body, exact configured public URL and parsed multi-value form parameters before signature-gated decoding; [ ] implement production Twilio event decoder, account/resource ownership checks and replay policy.
- [x] Implement AES-GCM encrypted tenant-scoped participant-address vault and opaque-reference resolver; [ ] wire it to a reviewed provider adapter and provision addresses through an audited administrative path.
- [ ] Implement Twilio conference creation/join semantics using the documented TwiML/Participants flow; do not assume a Conference can be directly created through the Conference resource.
- [ ] Implement provider reconciliation for timeout-after-acceptance, duplicate participant labels, concurrent joins, stale resources and account mismatch. Unknown outcomes must defer, never blindly retry.
- [ ] Gate recording start on joined-participant completeness and durable affirmative consent evidence for every participant.
- [ ] Implement recording stop/finalization, callback reconciliation and provider-side deletion.
- [x] Add a graceful polling worker loop and API liveness/readiness endpoints; [ ] wire concrete adapters, enforce provider timeouts below leases, implement lease renewal and service-manager supervision.
- [x] Add ordered migration runner, minimal API Docker image and local PostgreSQL/API staging Compose scaffold with externally injected environment values; [ ] deploy to isolated cloud staging, integrate a managed secret store/rotation, least-privilege provider credentials and verify backup/restore.

**Exit gate:** deterministic mock/contract tests cover the full lifecycle and crash windows; staging preflight confirms provider account configuration; no real call or production credential is used in CI.

### M4 — Media ingestion and verification

- [ ] Fetch completed media server-side using authenticated provider APIs; never trust arbitrary callback URLs.
- [x] Add bounded server-side WAV structural validation (RIFF/chunk lengths, PCM/IEEE-float format, frame alignment, duration, sample rate, channels, size and SHA-256); [ ] integrate media retrieval and full decoder validation for provider output formats.
- [x] Implement KMS-encrypted S3-compatible WAV object-storage adapter with tenant-derived opaque keys, SHA-256 metadata and 60–300 second presigned downloads; [ ] configure real bucket Block Public Access, least-privilege IAM/KMS, versioning/lifecycle and tenant-authorized retrieval.
- [ ] Verify channel semantics and analyze each channel independently (RMS/peak, silence, clipping, gaps, duration and sample rate).
- [ ] Require human or independently validated speech evidence for both directions; channel count or provider metadata alone is insufficient.
- [ ] Persist verification summary and provenance, not raw audio or transcript in logs.
- [ ] Implement provider-side and product-side retention/deletion reconciliation, including failed deletions and retryable tombstones.

**Exit gate:** synthetic integration tests plus consented staging recordings pass the complete media lifecycle; deletion is demonstrably complete across provider and product copies.

### M5 — Security, privacy and market readiness

- [x] Add a threat model covering tenant isolation, token theft, participant address exposure, webhook forgery/replay, consent bypass, SSRF, media leakage, outbox replay and local file protection; [ ] validate controls through independent security testing and close residual deployment risks.
- [x] Complete an engineering privacy/consent data-flow review and record fail-closed consent invariants; [ ] obtain jurisdiction-specific counsel approval of wording and actual capture topology.
- [ ] Complete data-protection impact assessment, lawful basis, data residency, retention defaults, user export/deletion and incident response with the selected market's counsel and privacy owner.
- [x] Add the app privacy manifest for currently used required-reason APIs; [ ] complete App Store privacy-label, permission, background-mode and recording-disclosure review against the final SDK/deployment configuration.
- [ ] Verify emergency-call exclusion and safe failure behavior; never silently record or bypass system disclosure.
- [ ] Run dependency, secret, static-analysis and backup/restore checks.

**Exit gate:** written legal/privacy/security approval for each market and release configuration. Engineering tests cannot substitute for this approval.

### M6 — Staging, production and controlled rollout

- [x] Add a local containerized staging scaffold with PostgreSQL, explicit migration job, API health checks and externally injected configuration; [ ] deploy a remote isolated provider subaccount/test-number staging environment with budget alerts.
- [x] Add ASGI lifecycle/tenant-isolation tests, PostgreSQL tenant/cancellation tests and WAV validation tests; [ ] run full provider-to-media end-to-end staging scenarios with consenting participants and verify both audio directions/cleanup.
- [ ] Exercise worker crash/restart, webhook replay, provider timeout, database failover, object-store outage and deletion retry.
- [x] Publish a pre-production incident/recovery/rollback runbook; [ ] implement dashboards, alerts, SLOs and support diagnostics from real staging telemetry.
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

1. Finish the M3 live-provider boundary: production Twilio event decoding/account ownership, audited participant-address provisioning, consent IVR and a concrete command adapter with reconciliation.
2. Complete M4 media retrieval, encrypted tenant object storage, two-sided/channel verification and provider/product deletion reconciliation.
3. Execute M2 physical iPhone/SIM/accessory/acoustic tests and publish the sanitized compatibility matrix; no software-only test can replace these.
4. Complete M5 jurisdiction-specific legal/privacy review, App Store privacy labels and independent security testing.
5. Deploy the local staging scaffold to an isolated remote environment, add real monitoring/alerts/rollback evidence, and configure Apple distribution signing.
6. Remove the five superseded branch refs and strengthen mainline ruleset enforcement when repository administration permissions are available.


## Verified repository controls (2026-11-19)

The active ruleset `protect main` targets the default branch and contains only `deletion` and `non_fast_forward` rules. It does not require pull requests, reviews or CI status checks. The GitHub integration could read the ruleset but received HTTP 403 for the legacy branch-protection endpoint, so no claim is made about additional legacy settings. No protection settings were changed. If stronger enforcement is desired, add a pull-request requirement and one always-present aggregate CI gate after its path-filtered job semantics are verified; do not require a workflow that is intentionally skipped for unrelated changes.

PR #45 (`fix/backend-consent-preflight`) was reviewed and squash-merged as `7bdfb89e53da159d7be8e0b45634202eda2d03c7` after Backend/PostgreSQL, Swift Core, repository policy, audio-analyzer and re-run iOS Simulator checks all passed on its exact head. It establishes durable pre-join consent and recording-from-start command semantics; it is not a live Twilio adapter or physical carrier proof. Superseded PRs #1, #9, #28 and #32 are closed after their useful changes were integrated. Issues #8 and #22 are now closed as duplicate/completed; #5 is narrowed to app-owned VoIP only; #20 is narrowed to physical-device evidence. The old branches `chore/agent-git-engineering-governance`, `chore/agent-rd-skills-and-templates`, `docs/recording-pathways-research`, `feat/ios-recording-retention-catalog-recovery` and `fix/ios-import-full-decode-validation` are superseded by merged work and should be deleted. The GitHub connector available for this run does not expose a delete-ref operation.
