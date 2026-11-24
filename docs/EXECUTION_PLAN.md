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


## Session progress — 2026-11-23

**Current main tip:** `048b54d71da483eaa5800e89ba2563627ccf2d7a`. A GitHub compare against the baseline `63ca46ed04dc519f6965a2759d1fbc42190a57eb` reports four commits ahead and **zero changed files**. Two temporary documentation commits were inadvertently written to main during branch creation, then immediately removed by revert commits; the tree is restored, but the add/revert commits remain in history. No force-push or history rewrite was used. This is recorded for audit transparency.

### Independent PRs opened

| Workstream | PR | Scope | Exact head | CI at last check |
|---|---|---|---|---|
| Plan / decisions | [#78](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/78) | Execution plan and conservative defaults | `72cd14c1fffe79c4f52a31fd925c03dae1d4ae80` | Queued |
| A1–A7 | [#79](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/79) | Ruleset JSON patch and admin read-back runbook | `f9d3a48f9d7b45f19c840202ed86e5679ce71f5d` | Queued |
| B1 | [#80](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/80) | Concurrent duplicate import regression test | `3f5cd0a4b30a967d36ef2e18652150cdf5daf829` | Latest head pending; earlier head still running and is superseded |
| D1 | [#81](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/81) | Physical iPhone/SIM tuple and per-run evidence matrix | `99de9c6150e91e905e09ee14a7941eb2ed29bce7` | Queued |
| G1 | [#82](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/82) | Sourced competitor/substitute matrix | `ba4bdaff02c4cc63ab2f1b688a6adf841e1131e4` | Queued |
| C1 | [#83](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/83) | Twilio adapter static review and live gates | `dd0cf63daf81cd8d40a47d327404d8f40547e54d` | Queued |
| E1 | [#84](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/84) | Guarded Terraform plan-only script and checklist | `27d409312113e12fc3b28dce094a4cdc1b3d64ee` | Latest head pending; earlier heads cancelled after updates |
| H1 | [#85](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/85) | Single-command worker default, cycle duration and runbook | `938fa24b430e4c6c44a0b6a140d34c6840233ded` | Pending |
| F1 | [#86](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/86) | Privacy/security release checklist | `fb8e77aa2b9f7107b2fa6f41a2bfbd3de0448bab` | Queued |

All listed PRs remain open and unmerged. CI is asynchronous; no PR is considered passed until the latest exact head has a completed successful Release Preflight.

### Updated evidence matrix

| Workstream | Done this session | PR | Blocked / next |
|---|---|---|---|
| A1–A7 | JSON patch and mandatory read-back runbook prepared | #79 | BLOCKED-ACCESS: connector supports Ruleset GET only; admin must apply and read back |
| B1 | Concurrent same-content import regression added; existing importer tests already cover corruption, truncation, storage reserve, recovery and duplicate backfill | #80 | Await XCTest exact-head result |
| C1 | Static review documented; consent, SID mapping, reconciliation and retry boundaries inspected | #83 | BLOCKED-ACCESS: live Twilio subaccount, two consenting test numbers, approved disclosure and spend cap |
| D1 | Tuple/run matrix created; all cells marked NOT RUN | #81 | BLOCKED-HARDWARE: physical iPhones, authorized SIMs and consenting participants |
| E1 | Account-guarded plan-only script and checklist created; no apply path | #84 | BLOCKED-ACCESS: approved AWS account ID, read-only credentials, network/certificate/DNS/secret/OIDC inputs |
| F1 | Privacy/security control-to-evidence checklist created | #86 | BLOCKED-EXTERNAL: independent security review, counsel/DPIA and physical/deployed evidence |
| G1 | Interview guide already exists; sourced competitor matrix added | #82 | BLOCKED-EXTERNAL: 15–20 interviews, 10 observed prototype tests, 5 qualified paid commitments |
| H1 | Default batch reduced to one command to reduce sequential lease starvation; cycle duration added to sanitized worker logs | #85 | No lease renewal or deployed metrics/alerts yet; await backend CI |

### New operational decision

The production worker now defaults to `WORKER_BATCH_SIZE=1` because dispatch is sequential while the lease starts at claim time. This reduces the risk that later commands in a large batch expire before execution. It is not a substitute for lease renewal and does not prove exactly-once provider execution.


## Follow-up verification — 2026-11-24

**Main snapshot:** `048b54d71da483eaa5800e89ba2563627ccf2d7a`. All nine work branches are present on the GitHub remote and all nine PRs are retargeted to `main` at this base. No local-only branch or unpushed commit is being represented.

### PR and exact-head CI evidence

| PR | Remote branch | Current head | Release Preflight evidence |
|---|---|---|---|
| [#78](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/78) | `docs/execution-plan-20261123` | `407a704dea99747044ff1c4f4000104b580a8424` | [Run 108](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45103210028) passed; this follow-up changes the branch and requires a fresh run |
| [#79](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/79) | `docs/main-ruleset-admin-patch-20261123` | `f9d3a48f9d7b45f19c840202ed86e5679ce71f5d` | [Run 104](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45103115439) passed |
| [#80](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/80) | `test/ios-import-concurrency-20261123` | `3f5cd0a4b30a967d36ef2e18652150cdf5daf829` | [Run 98](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45102947089) passed |
| [#81](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/81) | `docs/physical-device-matrix-20261123` | `99de9c6150e91e905e09ee14a7941eb2ed29bce7` | [Run 90](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45102770645) passed |
| [#82](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/82) | `research/competitor-matrix-20261123` | `ba4bdaff02c4cc63ab2f1b688a6adf841e1131e4` | [Run 91](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45102794822) passed |
| [#83](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/83) | `docs/twilio-adapter-review-20261123` | `dd0cf63daf81cd8d40a47d327404d8f40547e54d` | [Run 94](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45102829556) passed |
| [#84](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/84) | `chore/terraform-plan-only-guard-20261123` | `27d409312113e12fc3b28dce094a4cdc1b3d64ee` | [Run 106](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45103171907) passed |
| [#85](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/85) | `fix/outbox-worker-lease-safety-20261123` | `a504cdb51f9c6ace8fcb44d98b5e8ad637d70c3c` | New exact-head Release Preflight [Run 109](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45323789850) queued; previous head's green run does not certify this correction |
| [#86](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/86) | `docs/privacy-security-checklist-20261123` | `fb8e77aa2b9f7107b2fa6f41a2bfbd3de0448bab` | [Run 99](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45102962739) passed |

The completed Release Preflight runs each reported successful jobs for the relevant workflow, including repository policy, Swift core, XCTest simulator targets, PostgreSQL 16/17, audio analyzer and Terraform validate where present. These are CI/simulator/source validations, not physical SIM or live provider tests.

### Follow-up correction in H1

The worker test fake now respects the dispatcher's requested `limit`. The prior fake returned three outcomes when called with `limit=1`, making the assertion inconsistent with the dispatch contract. The corrected test slices outcomes to the requested limit and asserts one claimed/acknowledged command. Commit: `a504cdb51f9c6ace8fcb44d98b5e8ad637d70c3c`. Its exact-head CI is pending as noted above.

### Live governance read-back

Ruleset ID `27591151` is active, but the actual GET read-back still contains only `deletion` and `non_fast_forward`. It does **not** yet contain required PR reviews, required status checks, linear history or conversation resolution. The prepared JSON is not proof of an applied ruleset. Do not mark A1–A7 complete and do not merge these PRs until an authorized administrator applies the payload and the live GET confirms the intended rules.

### Current evidence matrix

| Workstream | Status | PR | Exact-head CI | Remaining external gate |
|---|---|---|---|---|
| A1–A7 | PATCH PREPARED; live config incomplete | #79 | PASS | BLOCKED-ACCESS: admin apply + GET read-back |
| B1 | Regression test added | #80 | PASS | Physical file-provider/device coverage remains separate |
| C1 | Static adapter review complete | #83 | PASS | BLOCKED-ACCESS: live Twilio account, two consenting numbers, approved disclosure and spend cap |
| D1 | Test matrix/protocol prepared; all results NOT RUN | #81 | PASS (docs only) | BLOCKED-HARDWARE: physical iPhones, SIMs, carriers and participants |
| E1 | Guarded plan-only script + tests prepared | #84 | PASS | BLOCKED-ACCESS: approved AWS account/role and non-secret staging inputs; no plan run performed |
| F1 | Privacy/security checklist prepared | #86 | PASS (docs only) | BLOCKED-EXTERNAL: counsel, DPIA, independent security review and deployed evidence |
| G1 | Competitor research and interview kit prepared | #82 | PASS (docs only) | BLOCKED-EXTERNAL: actual interviews, observed tests and qualified commitments |
| H1 | Batch default + sanitized cycle timing + corrected limit test | #85 | PENDING on current head | Lease renewal, durable metrics/alerts and live provider crash-window evidence |

**Merge policy:** PRs remain open and unmerged. The latest exact-head CI must pass and the live governance configuration must be verified before merge. No PR merge is implied by a green CI run.
