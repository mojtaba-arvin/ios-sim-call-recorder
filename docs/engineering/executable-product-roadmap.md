# Executable Product Roadmap

**Snapshot:** 2026-11-22  
**Purpose:** turn the repository's research and implementation into a sequenced, evidence-gated delivery plan. This is a living execution document, not a claim that hardware, carrier or production work has passed.

 > **Execution update (2026-11-22):** PR #54 is merged as `dac0d409388af1623bbebd51306537ad0f842d56`; its Release Preflight passed all nine matrix-expanded checks on final PR head `7938c89c7053eee2ec0cc9b799f36b489aa9b00f` (Run `44995777499`). PR #55's Backend, Infrastructure, Repository Policy and nine Release Preflight checks passed on head `e2d0ebe81af8cbe24f3ba3c59eb0679a66b5eea4`; no live Twilio call was performed. PR #57 proposes CI deduplication and a shorter iOS critical path; its checks are still running. This does not establish live Twilio, physical SIM/carrier, AWS staging, legal or App Store acceptance. PR #53 is closed but not merged. The detailed blockers and acceptance criteria are tracked in [Next execution roadmap](../release/next-execution-roadmap.md).

## Product boundary and release definition

The product has two distinct modes and they must not be conflated:

1. **Native-call companion:** the user obtains a recording through an OS/carrier/accessory-supported route and explicitly imports it. The app manages, validates, plays, exports and deletes the file. It does not intercept Phone.app audio.
2. **App-owned/provider bridge:** the backend coordinates provider call legs and records a conference after all required participants have received disclosure and affirmatively consented. This does not prove that a carrier can merge an existing SIM call into the bridge.

A release may claim support only for exact device, OS build, region, carrier/plan, SIM/network, accessory and call-topology tuples that pass the acceptance protocol. No universal carrier, device or two-way-capture claim is permitted.

## Current baseline

### Implemented in main (software evidence)

- Swift recording core and cancellation/resource-lifecycle behavior.
- VoiceOver status announcements, accessibility labels/identifiers and Dynamic Type-compatible system text styles; physical accessibility review remains open.
- Low-storage import preflight with a 64 MiB reserve, finite UIKit background-execution lease for user-initiated imports, foreground catalog/staging recovery and explicit complete file protection for production media/catalog files.
- Bundled PrivacyInfo.xcprivacy declaring app-owned UserDefaults (CA92.1) and disk-space access (E174.1); signing and full App Store review remain open.
- SwiftUI companion shell with user-mediated file import, app-private storage, local catalog, playback, seeking, system share/export, opt-in retention and catalog recovery.
- WAV RIFF/chunk boundary checks and bounded AVFoundation decode validation are merged in PR #40; software import validation is complete for the covered formats and fixtures.
- Audio quality analyzer and deterministic WAV fixtures.
- Provider-neutral bridge state machine, consent gate, signed-webhook verification boundary, PostgreSQL persistence, transactional outbox, lease-based dispatcher, reconciliation contract and immutable provider-resource mappings.
- Authenticated tenant-scoped ASGI session create/read/cancel component, PostgreSQL tenant ownership, liveness/readiness endpoints and ordered migration runner.
- Live Twilio REST command adapter for consent calls, Conference participant creation/addition and close; explicit DTMF Gather consent; signed account-bound call-status/Conference/Recording webhooks; separate immutable mappings for consent calls and conference legs; tenant-scoped encrypted address provisioning with audit events; supervised outbox and retention worker entry points. PR #52 adds the code path, but live account acceptance is not claimed. This is an app-owned outbound two-party conference, not proof of native SIM-call merge or Phone.app audio capture.
- Bounded server-side WAV structural validation with digest, format, channel-count, sample-rate, duration and chunk-boundary checks.
- KMS-encrypted S3-compatible WAV object-storage adapter with tenant-derived opaque keys, validation-before-upload and bounded presigned download URLs.
- CI workflows for Swift, iOS Simulator, audio analysis, backend/PostgreSQL and repository policy.

### Implemented foundations and remaining external acceptance

- Production ASGI composition root and signed webhook ingress are implemented. AWS ECS/RDS/S3/KMS/ALB Terraform and a manual OIDC deployment workflow are prepared, but no AWS account, DNS, ACM certificate, secret or cloud environment has been provisioned. Rate limiting and automated secret rotation remain open.
- Live Twilio adapter and consent/webhook/media routes are implemented in PR #52; live Twilio account preflight, billing, real outbound-call acceptance, conference callback ordering and account-level dual-channel recording setting remain unverified.
- A standalone supervised outbox worker, cancellation of outstanding consent calls and provider-backed Conference close adapter are implemented; long-running lease renewal and provider-side cancellation reconciliation for every edge case remain open.
- Twilio Conference recording retrieval with RequestedChannels=2, bounded WAV validation, two-channel activity verification, deterministic channel ownership metadata for exactly two expected participants, KMS-backed S3 upload, session verification finalization and retryable Twilio/S3 retention deletion. Rejected/oversized media is retained as a rejection record for provider cleanup; verified media is available only through a tenant-authorized 120-second presigned URL with audit. Channel 1 is the first conference participant; channel 2 is all remaining audio. With exactly two participants this separates the two legs, but it is not biometric speaker identification.
- Physical iPhone/carrier/accessory evidence for two-way intelligible capture.
- Legal review and App Store approval for each launch market.
- Production deployment or end-to-end paid provider call.

## Product validation gate (before production-scale investment)

The detailed evidence, customer-discovery protocol, segment hypotheses, competitor/substitute analysis and go/no-go criteria live in [Product validation](../research/product-validation.md). The executable substitutes are the [remote physical-device test kit](../validation/remote-device-validation-kit.md), [customer discovery and paid-pilot kit](../validation/customer-discovery-kit.md), [Twilio unit-economics baseline](../research/unit-economics.md) and [counsel brief](../legal/counsel-brief.md).

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
- [x] Merge PR #54 and verify its unified `release-preflight.yml` (nine matrix-expanded checks on its final head). PR #57 now consolidates PR validation into that workflow, keeps the backend Compose lifecycle as a unique path-filtered check, and makes duplicate standalone checks manual-only; its final CI is pending. [ ] Apply and read back the required PR/status-check/linear-history/force-push rules on `protect main`; current Ruleset ID 27591151 contains only `deletion` and `non_fast_forward`.
- [x] Publish the post-PR #52 dependency/workstream map in [Next execution roadmap](../release/next-execution-roadmap.md). [ ] Reconcile branch hygiene against the live GitHub inventory: only `main` and `chore/cross-repo-engineering-baseline` were present before PR #54; PR #53 is closed/unmerged and its branch is a deletion candidate after unique-commit/open-PR checks. Do not act on the historical five-branch count without fresh branch evidence.

**Exit gate:** clean mainline; all required checks green; no duplicate stacked PRs; one source of truth for project scope, evidence and release gates.

### M1 — Finish the native-call companion

- [x] User-mediated import and private local storage.
- [x] Local playback, seeking, interruptions/output-route handling and user-initiated export.
- [x] Opt-in retention, backup catalog recovery and fail-closed storage behavior.
- [x] Complete import adversarial cases on the current mainline with PR #40; keep format-specific claims bounded by decoder evidence.
- [x] Add VoiceOver status announcements, accessible status/progress semantics and Dynamic Type-compatible system typography; [ ] complete physical VoiceOver/Switch Control/Dynamic Type review on device.
- [x] Add low-storage preflight, finite UIKit background-execution lease and foreground recovery of interrupted imports/catalog/staging; [ ] execute physical low-storage/process-kill scenarios and verify lease-expiration behavior.
- [x] Apply complete file protection to production media and catalog files and exclude app storage from backups; [ ] verify lock/reboot/first-unlock behavior on a physical device.
- [x] Bundle PrivacyInfo.xcprivacy with the UserDefaults and DiskSpace required-reason declarations; [ ] complete transitive SDK/privacy-label review.
- [ ] Configure Apple Developer Team, distribution signing identity/provisioning and reproducible signed Release archive; credentials are not available in this repository workflow.

### M3 — Backend and provider execution

- [x] Authenticated tenant-scoped ASGI session API and ordered PostgreSQL migrations.
- [x] Transactional initial consent-request outbox commands and durable affirmative/decline evidence.
- [x] Twilio REST adapter for consent calls, conference participant creation/addition, recording-from-start, dual-channel requests and resource reconciliation.
- [x] Signed webhook routes for consent, call status, Conference and Recording callbacks; account-scoped resolver maps consent call SIDs separately from Conference participant SIDs.
- [x] Encrypted address vault provisioning API and metadata-only audit trail.
- [x] Standalone worker entry point; outstanding consent calls are cancelled on decline/cancel and no new consent calls are dialed for terminal sessions.
- [ ] Run a live Twilio account preflight and a controlled, consented test call. No live PSTN call has been made from this session.

### M4 — Media retrieval and retention

- [x] Download completed Twilio Conference recordings with RequestedChannels=2 and verify stereo PCM16 plus audible activity in both channels.
- [x] Restrict the current bridge to exactly two expected participants; persist channel 1/2 ownership mapping, digest, duration and verification outcome.
- [x] Store verified media with KMS encryption and run two-phase Twilio/S3 retention deletion.
- [ ] Verify a live Twilio dual-channel recording, provider-side deletion and S3 deletion in an authorized account.

### M5 — Legal and product trust

- [x] Engineering consent/PII boundaries, address provisioning audit, counsel-ready legal brief and explicit DTMF consent flow.
- [ ] Select launch jurisdiction, obtain counsel approval of the exact disclosure and data flow, complete App Store review and signed distribution.

### M6 — Production foundations

- [x] AWS Terraform for ALB HTTPS, ECS Fargate, private RDS, KMS/S3, Secrets Manager integration, CloudWatch logs/alarm and OIDC deploy role.
- [x] Manual staging deployment workflow runs migrations before service rollout and checks readiness.
- [ ] Bootstrap AWS VPC/subnets, ACM certificate, DNS and Secrets Manager JSON secret; apply Terraform and validate actual cloud deployment. No AWS resources have been created.
- [ ] Add rate limits, secret rotation, outbox/dead-letter dashboards, provider error alerts and rollback drills.

**Exit gate:** app builds from a clean checkout; import/play/export/delete/retention survive relaunch and interruption; accessibility and privacy review evidence attached. This mode remains a companion/import app, not a native Phone-call recorder.

### M2 — Prove a real capture pathway

Run the tracks in parallel; do not select a pathway from documentation alone.

- [ ] **Apple native recording:** test availability by OS, physical region and language; test user export/import and artifact integrity. Do not assume Notes private APIs.
- [ ] **Carrier conference merge:** on consenting test SIMs, verify add-call/merge, hold, call waiting, interruption and hang-up behavior for inbound and outbound calls. PR #52's Twilio outbound conference is a separate app-owned call flow and does not establish that the user's existing SIM call can be merged or captured.
- [ ] **External HFP/wired accessory:** identify a specific accessory and signal path; prove both uplink and downlink are present in the saved artifact. Pairing or microphone access alone is not proof.
- [ ] **Acoustic fallback:** measure speakerphone plus independent recorder in controlled noise/distance conditions.
- [ ] For each positive tuple, repeat at least three calls and independently verify local and remote speech; record exact model, iOS build, region, carrier/plan, SIM, network, route, accessory firmware, consent and signal metrics.

**Exit gate:** at least one lawful repeatable pathway has three positive two-way samples on an explicitly named compatibility tuple. Otherwise ship only the companion/import capability and state that recording capture is not supported.

### M3 — Turn the backend foundation into a deployable service

- [x] Implement authenticated tenant-scoped ASGI session create/read/cancel component and PostgreSQL tenant ownership; [ ] add durable API idempotency, rate limits and production token rotation.
- [ ] Implement canonical public-origin configuration and trusted-proxy handling; reject arbitrary forwarded-host reconstruction.
- [x] Implement bounded signed-webhook ASGI transport that preserves raw body, exact configured public URL and parsed multi-value form parameters before signature-gated decoding; [x] add strict account-bound Twilio consent/Conference/Recording event normalization with opaque resource resolution (PR #51); [ ] mount the routes in the production ASGI app and verify the full provider callback/replay lifecycle.
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
- [x] Add ASGI lifecycle/tenant-isolation tests, PostgreSQL tenant/cancellation tests, API-to-PostgreSQL lifecycle integration test, webhook ingress, address-vault and media-storage tests; [ ] run full provider-to-media end-to-end staging scenarios with consenting participants and verify both audio directions/cleanup.
- [ ] Exercise worker crash/restart, webhook replay, provider timeout, database failover, object-store outage and deletion retry.
- [x] Publish a pre-production incident/recovery/rollback runbook and implement basic API liveness/readiness plus redacted worker-cycle logs; [ ] implement dashboards, alerts, SLOs and support diagnostics from real staging telemetry.
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

1. Finish the M3 live-provider boundary: mount the Twilio event routes, add audited participant-address provisioning, implement the consent IVR and concrete command adapter with reconciliation.
2. Complete M4 media retrieval, encrypted tenant object storage, two-sided/channel verification and provider/product deletion reconciliation.
3. Execute M2 physical iPhone/SIM/accessory/acoustic tests and publish the sanitized compatibility matrix; no software-only test can replace these.
4. Complete M5 jurisdiction-specific legal/privacy review, App Store privacy labels and independent security testing.
5. Deploy the local staging scaffold to an isolated remote environment, add real monitoring/alerts/rollback evidence, and configure Apple distribution signing.
6. Remove the five superseded branch refs and strengthen mainline ruleset enforcement when repository administration permissions are available.


## Verified repository controls (2026-11-19)

The active ruleset `protect main` targets the default branch and contains only `deletion` and `non_fast_forward` rules. It does not require pull requests, reviews or CI status checks. The GitHub integration could read the ruleset but received HTTP 403 for the legacy branch-protection endpoint, so no claim is made about additional legacy settings. No protection settings were changed. If stronger enforcement is desired, add a pull-request requirement and one always-present aggregate CI gate after its path-filtered job semantics are verified; do not require a workflow that is intentionally skipped for unrelated changes.

PR #45 (`fix/backend-consent-preflight`) was reviewed and squash-merged as `7bdfb89e53da159d7be8e0b45634202eda2d03c7` after Backend/PostgreSQL, Swift Core, repository policy, audio-analyzer and re-run iOS Simulator checks all passed on its exact head. It establishes durable pre-join consent and recording-from-start command semantics; it is not a live Twilio adapter or physical carrier proof. Superseded PRs #1, #9, #28 and #32 are closed after their useful changes were integrated. Issues #8 and #22 are now closed as duplicate/completed; #5 is narrowed to app-owned VoIP only; #20 is narrowed to physical-device evidence. The old branches `chore/agent-git-engineering-governance`, `chore/agent-rd-skills-and-templates`, `docs/recording-pathways-research`, `feat/ios-recording-retention-catalog-recovery` and `fix/ios-import-full-decode-validation` are superseded by merged work and should be deleted. The GitHub connector available for this run does not expose a delete-ref operation.
