# Execution Plan — 2026-11-23

**Repository:** `mojtaba-arvin/ios-sim-call-recorder`  
**Baseline:** `main` at `63ca46ed04dc519f6965a2759d1fbc42190a57eb`  
**Release status:** BLOCKED — automated software checks pass, but governance enforcement and external acceptance remain incomplete.

## Operating rules

- Each independent workstream gets its own task-scoped branch and PR targeting `main`.
- Never merge automatically, push to `main`, force-push, apply AWS resources, initiate paid Twilio/PSTN calls, or publish a release.
- CI is evidence only for the exact tested commit. Simulator tests are not physical cellular-call evidence.
- Use `BLOCKED-ACCESS` for unavailable account/API authority and `BLOCKED-HARDWARE` for missing physical devices/SIMs. Continue independent documentation and code work.
- Keep secrets, phone numbers, raw recordings, signed media URLs and participant data out of GitHub artifacts.

## Live baseline

- Latest main commit: `63ca46ed04dc519f6965a2759d1fbc42190a57eb` (2026-11-22 18:27 UTC).
- Release Preflight run **#84**, run ID `45055147455`, on the exact main SHA above: completed **success** (8 jobs, including PostgreSQL 16/17 and iPhone 16/iPhone 16 Pro simulator tests). This is not live Twilio, physical-device, AWS deployment or legal evidence.
- Active Ruleset `protect main`, ID `27591151`, targets `~DEFAULT_BRANCH`; currently only `deletion` and `non_fast_forward` are configured. Bypass list is empty. Required PR/check/linear-history rules are absent.
- Repository metadata reports admin permission, but the available GitHub integration exposes ruleset GET only and no ruleset mutation operation. Do not infer that admin permission means this session can apply it.
- Issues: #18 physical SIM merge/audio topology; #48 product/customer validation; #56 privileged main ruleset action.
- The repo already contains a physical-device protocol, remote tester kit, Twilio live acceptance harness (dry-run by default), customer discovery kit, threat model, Terraform stack and main-ruleset apply script. These are prepared artifacts, not completed external validation.
- No `DECISIONS.md` existed at baseline; this file records reversible execution defaults until a canonical ADR is created.

## Workstream status and next action

| ID | Workstream | Status | Evidence / dependency | Next action |
|---|---|---|---|---|
| A1 | Governance / Ruleset | BLOCKED-ACCESS | Ruleset 27591151 read back; required rules absent; integration has GET only | Supply canonical JSON payload, safe apply/read-back command and exact eight checks; human admin executes |
| A2–A7 | Governance controls | BLOCKED-ACCESS | PR requirement, required checks, linear history, force-push restriction, deletion restriction, empty bypass actors | Verify each rule after privileged apply; no success claim from local script |
| B1 | Import reliability / iOS Companion | IN PROGRESS | Batch import, streaming SHA-256 duplicate detection and catalog recovery exist on main; simulator XCTest passes in run #84 | Review importer failure/cancellation/partial-file/catalog consistency tests; add only missing regression coverage in isolated PR |
| C1 | Twilio adapter review | IN PROGRESS | Concrete adapter, consent IVR, signed account-scoped callbacks, reconciliation and dual-channel WAV validation exist | Audit idempotency, timeouts, ambiguous provider side effects, callback ordering, recording lifecycle and deletion; live acceptance remains blocked |
| D1 | Physical iPhone/SIM matrix | BLOCKED-HARDWARE | Protocol and remote validation kit exist; Issue #18 open | Use two physical iPhones, authorized SIMs and consenting participants; record exact tuple and per-channel evidence; no simulated substitute |
| E1 | Terraform / staging plan | BLOCKED-ACCESS | Terraform source and validate workflow exist; no AWS account/role/network/certificate/secret evidence | Review source and prepare backendless plan procedure; no cloud plan/apply without account and explicit approval |
| F1 | Threat model / privacy | IN PROGRESS | Threat model updated 2026-11-22; explicitly not pen test/legal opinion | Review residuals, map mitigations to evidence, keep legal/security sign-off external |
| G1 | Customer discovery | PREPARED / BLOCKED-EXTERNAL | Interview/pilot kit exists; Issue #48 requires interviews, observed prototype use and paid commitments | Keep segment as hypothesis; execute 15–20 interviews, 10 observed tests, 5 qualified paid commitments; no invented outcomes |
| H1 | Outbox / idempotency / retry / observability | IN PROGRESS | Transactional outbox, lease dispatcher, DB idempotency and reconciliation foundations exist | Inspect worker crash windows, lease expiry, retry taxonomy, dead-letter visibility, metrics/alerts and concurrency tests; avoid claiming exactly-once provider effects |

## Dependency order

1. Governance payload/runbook can be prepared independently; privileged application and read-back are external.
2. B1 importer tests, C1 adapter audit, F1 threat-model review and G1 discovery materials can proceed independently.
3. D1 physical testing requires real devices/SIMs and consenting participants; it is not unblocked by simulator CI.
4. E1 Terraform static validation is independent; AWS plan/apply requires approved account access and explicit authorization.
5. H1 worker improvements depend on current backend code and PostgreSQL tests, not live Twilio.
6. Release remains blocked until all required governance, provider, physical, AWS and legal evidence is reviewed.

## Evidence matrix

| Workstream | Done | PR | CI | Blocked | Evidence | Next |
|---|---|---|---|---|---|---|
| A1–A7 | Payload/runbook to be supplied | Pending | Pending | BLOCKED-ACCESS | Ruleset GET shows only deletion + non_fast_forward | Admin apply and GET read-back |
| B1 | Existing import hardening | Pending review | Run #84 passed | None for static review | Main SHA and simulator jobs | Inspect missing edge cases |
| C1 | Existing adapter implementation | Pending review | Run #84 backend jobs passed | BLOCKED-ACCESS for live Twilio | Issue #16 update and harness | Contract audit; then authorized staging |
| D1 | Protocol and kit prepared | Pending | Not applicable | BLOCKED-HARDWARE | docs/engineering/physical-device-test-protocol.md | Execute exact tuple |
| E1 | Terraform source | Pending review | Run #84 terraform-validate passed | BLOCKED-ACCESS for AWS | infra/aws and CI validation | Backendless plan only |
| F1 | Threat model prepared | Pending review | Run #84 repository-policy passed | External security/legal review | docs/security/threat-model.md | Residual-control audit |
| G1 | Discovery kit prepared | Pending | Not applicable | BLOCKED-EXTERNAL | docs/validation/customer-discovery-kit.md | Conduct interviews/tests |
| H1 | Durable foundations present | Pending review | Run #84 backend jobs passed | Live provider confirmation | backend outbox/worker tests | Audit and focused regression tests |

## Release gate

Do not mark release-ready until: (1) ruleset is read back with all required rules and eight check identities, (2) real Twilio staging acceptance includes consent, callbacks, verified two-channel media and deletion, (3) exact physical iPhone/SIM/carrier tuples pass repeatable two-way tests, (4) AWS staging is explicitly approved, deployed, health-checked and rollback-tested, and (5) jurisdiction-specific legal/privacy review is written and approved.
