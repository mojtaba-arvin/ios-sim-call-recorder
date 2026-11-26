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


## Final branch and CI snapshot — 2026-11-24 08:10 +04:00

All nine PRs are open, all target `main`, and all heads are pushed to the GitHub remote. The current main/base SHA is `048b54d71da483eaa5800e89ba2563627ccf2d7a`. PR #78 contains this evidence update; use its current GitHub head SHA rather than a copied prior snapshot.

| PR | Current head SHA | Current CI evidence |
|---|---|---|
| #79 | `4d08819d4930f67dc1c2e41f16692e0a2eec4e60` | Release Preflight pending/in progress on this exact head; prior head passed but does not certify the payload-file refactor |
| #80 | `3f5cd0a4b30a967d36ef2e18652150cdf5daf829` | PASS — [Run 98](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45102947089) |
| #81 | `99de9c6150e91e905e09ee14a7941eb2ed29bce7` | PASS — [Run 90](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45102770645) |
| #82 | `ba4bdaff02c4cc63ab2f1b688a6adf841e1131e4` | PASS — [Run 91](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45102794822) |
| #83 | `89bc3f498f2df890d3fec810858bbcf706c1099b` | Backend staging integration PASS — [Run 45324147457](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45324147457); Release Preflight in progress — [Run 45324147613](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45324147613) |
| #84 | `27d409312113e12fc3b28dce094a4cdc1b3d64ee` | PASS — [Run 106](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45103171907) |
| #85 | `4bb1f8459f9849fc2eb00874b5caea3670f0e760` | Backend staging integration in progress — [Run 45324235480](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45324235480); Release Preflight pending — [Run 45324235224](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45324235224) |
| #86 | `fb8e77aa2b9f7107b2fa6f41a2bfbd3de0448bab` | PASS — [Run 99](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45102962739) |

### Latest code refinements
- **C1 / PR #83:** the unused adapter timeout option was removed. Both ASGI and worker composition roots now apply bounded `TWILIO_REQUEST_TIMEOUT_SECONDS` (default 10 seconds, range 1–12) to the actual Twilio SDK client. `backend/tests/test_config.py` covers default, override, malformed and out-of-range values. The worker batch default remains one command.
- **H1 / PR #85:** the production worker entry point explicitly defaults `WORKER_BATCH_SIZE` to one. The fake dispatcher in tests now respects the requested `limit`, and a regression assertion checks the production entry-point default. Exact-head Release Preflight is pending.

### Live governance re-check
Ruleset `27591151` remains active on `~DEFAULT_BRANCH`, with empty bypass actors, but its live rules are still only `deletion` and `non_fast_forward`. The prepared six-rule payload has not been applied. PRs remain open and unmerged; do not treat CI success or a prepared JSON payload as governance approval.


## Final verification and disposition — 2026-11-24 09:20 +04:00

All nine open workstream PRs target `main`; their current head SHAs are pushed and their latest exact-head Release Preflight runs have completed successfully. This supersedes the pending/in-progress statuses in earlier session snapshots.

| PR | Head SHA | Latest exact-head Release Preflight |
|---|---|---|
| [#78](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/78) | `f6d44cf4e7352f88e6712e54f5c7a75041bd2f33` | [45324396668](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45324396668) — PASS |
| [#79](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/79) | `4d08819d4930f67dc1c2e41f16692e0a2eec4e60` | [45323914351](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45323914351) — PASS |
| [#80](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/80) | `3f5cd0a4b30a967d36ef2e18652150cdf5daf829` | [45102947089](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45102947089) — PASS |
| [#81](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/81) | `99de9c6150e91e905e09ee14a7941eb2ed29bce7` | [45102770645](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45102770645) — PASS |
| [#82](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/82) | `ba4bdaff02c4cc63ab2f1b688a6adf841e1131e4` | [45102794822](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45102794822) — PASS |
| [#83](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/83) | `89bc3f498f2df890d3fec810858bbcf706c1099b` | [45324147613](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45324147613) — PASS |
| [#84](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/84) | `27d409312113e12fc3b28dce094a4cdc1b3d64ee` | [45103171907](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45103171907) — PASS |
| [#85](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/85) | `4bb1f8459f9849fc2eb00874b5caea3670f0e760` | [45324235224](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45324235224) — PASS |
| [#86](https://github.com/mojtaba-arvin/ios-sim-call-recorder/pull/86) | `fb8e77aa2b9f7107b2fa6f41a2bfbd3de0448bab` | [45102962739](https://github.com/mojtaba-arvin/ios-sim-call-recorder/actions/runs/45102962739) — PASS |

For runs #78, #79, #83 and #85, the job-level read-back confirms successful completion of both iPhone 16 and iPhone 16 Pro XCTest simulator jobs, Swift core, audio analyzer, PostgreSQL 16 and 17, Terraform validate, and repository-policy jobs. The other five exact-head runs also completed successfully. These remain hosted simulator and CI results, not physical SIM, real carrier, live Twilio, AWS deployment or legal acceptance.

### Merge and governance decision

The live GET of repository Ruleset `27591151` was repeated at this checkpoint. It remains active and targets `~DEFAULT_BRANCH`, but the only configured rules are `deletion` and `non_fast_forward`. There are no required pull-request approvals, no required status-check rules, no linear-history rule, and no conversation-resolution rule. The bypass actor list is empty. The GitHub connection available to this execution can read rulesets but has no ruleset mutation action. The prepared payload in PR #79 is therefore still unapplied.

**Decision: do not merge the nine PRs yet.** All nine latest exact-head CI runs are green, but the governance gate explicitly requires an administrator to apply the canonical ruleset payload and verify the resulting live GET. No review submissions exist on these PRs. Do not bypass the missing governance gate merely because the current GitHub configuration would permit a merge.

### Remaining dispositions

| Area | Disposition | What closes it |
|---|---|---|
| Ruleset / governance | BLOCKED-ACCESS | Repository administrator applies `docs/governance/main-ruleset-payload.json` through an authorized GitHub Administration write path, then verifies exact rules and check names by GET |
| Twilio | BLOCKED-ACCESS / external acceptance | Authorized staging subaccount, two consenting test numbers, approved disclosure and jurisdiction, spend cap; execute the documented harness and retain sanitized callback/media/deletion evidence |
| SIM call capture and HFP | BLOCKED-HARDWARE | Physical iPhones, SIMs/carriers, accessory and consenting participants; record exact device/iOS/carrier tuple and two-way channel evidence |
| AWS | BLOCKED-ACCESS | Approved account/role and complete non-secret staging inputs; run plan-only review first. No apply without a separate explicit deployment approval |
| Legal/privacy | BLOCKED-EXTERNAL | Written jurisdiction-specific counsel review and retention/disclosure approval |
| Customer discovery | BLOCKED-EXTERNAL | Actual interviews, observed prototype tests and qualified paid-pilot evidence; no inferred demand |

No paid Twilio calls, AWS resources, production deployments, fabricated physical-device results or legal approvals were created or claimed. Release remains BLOCKED until all release gates above are independently evidenced.


## Current verified state — 2026-11-24 14:20 +04:00 (supersedes stale snapshots above)

- Current `main`: `c2d3b23ccdb84aec8585b3a296b05eec3c241524`; PR #79 was squash-merged after all eight required Release Preflight checks passed on its exact head.
- Ruleset `27591151` was read back after the administrator's update: active on `refs/heads/main`, no bypass actors, five supported rule types (`deletion`, `non_fast_forward`, `required_linear_history`, `pull_request` with review-thread resolution, and strict `required_status_checks`) and the exact eight required contexts. Governance is VERIFIED; earlier statements that only two rules were present are historical and superseded.
- PR #78 and #80–#87 remain open. Their branches have been updated to include current main via merge commits; compare against current main reports zero commits behind and each PR reports mergeable. Fresh Release Preflight runs are in progress/queued on the updated heads. Do not merge until all eight required checks succeed on the exact current head.
- PR #83 and #85 both modify `backend/worker_main.py`. Their current branch changes are independently testable, but the later merge must reconcile bounded Twilio HTTP timeout configuration with the one-command worker batch default; do not discard either behavior.
- Release remains BLOCKED for external evidence: physical iPhone/SIM/carrier validation, live Twilio acceptance, AWS staging authorization/deployment, customer discovery, and jurisdiction-specific legal/privacy approval. Simulator CI is not evidence for physical SIM capture or carrier capability.
- No AWS resources, paid Twilio calls, production deployment, physical-device tests, customer interviews, or legal approvals are claimed.


## Current verified checkpoint — 2026-11-26 07:26 +04:00

This checkpoint supersedes the earlier 2026-11-23/24 snapshots above.

### Mainline and engineering PRs

- Main is 72a3d0d71e2729c3f8e107635709c56602a079b4.
- PR #92 merged as 6d4b970754c1c4593e587d7aff0f782da4da7370: per-recording retention deletion claims, five-minute lease, random token fencing, durable provider/object-store stage progress, retry backoff and PostgreSQL 16/17 recovery/concurrency coverage.
- PR #97 merged as 72a3d0d71e2729c3f8e107635709c56602a079b4: sanitized retention cycle success/failure telemetry and durable retry events. Exact-head Release Preflight passed all eight jobs; Backend staging integration passed on an isolated CI stack. This is not AWS staging deployment or live Twilio/S3 acceptance.
- PR #94 was closed as stale after #97 advanced main. Its carrier register was recreated from the current main as PR #98 on branch docs/carrier-capability-register-20261126. Do not merge until all required exact-head checks pass.
- PR #98 is documentation-only: the carrier capability register and forwarding protocol keep C-001 UNKNOWN and FWD-01..04 NOT RUN. No country, operator, plan or carrier capability is certified.
- The earlier PR #93 documentation branch is stale/diverged; this PR refreshes the canonical decision, execution and runbook documents on a new current-main branch.

### Operational evidence and product gates

| Gate | Status | Evidence needed to close |
|---|---|---|
| Retention deletion implementation | ENGINEERING COMPLETE | Already merged; keep at-least-once/idempotent wording |
| Retention worker observability | ENGINEERING COMPLETE | #97 merged; validate emitted logs in deployed AWS |
| CloudWatch alerting | BLOCKED-ACCESS | Provision metric filters, alarms and notification destination; trigger and verify test alarm |
| Carrier capability register | DOCUMENTED / NOT VALIDATED | #98 merge, then official operator evidence and physical SIM tests |
| Native SIM capture / conference merge | BLOCKED-HARDWARE | Physical iPhone/SIM/carrier tests with consenting participants and per-channel audio evidence |
| Twilio provider acceptance | BLOCKED-ACCESS / EXTERNAL | Authorized staging account, test numbers, disclosure approval, callback/media/deletion evidence |
| AWS staging | BLOCKED-ACCESS | Approved AWS account/role, Terraform provisioning, deploy, readiness checks and rollback |
| Customer / legal validation | BLOCKED-EXTERNAL | Selected jurisdiction/segment, interviews, observed prototype tests, paid-pilot evidence and written legal/privacy review |

### Current product decision

Do not add more recording features until the real capture pathway and initial buyer segment are validated. Keep TWILIO_ENABLED=false until authorized provider staging and consent/legal gates pass. Do not describe the app-owned Twilio Conference as native SIM-call recording. Keep product release BLOCKED.


## Verified checkpoint — 2026-11-26 14:00 +04:00

- PR #98 merged to main as `7d3e8d0f083d99b265879d9a584bb3bcdd9a74a3`; carrier register is now in main, but all operator/country capabilities remain UNKNOWN until primary-source or physical evidence exists.
- PR #99 and #100 were recreated from this new main tip because D-EXEC-011 requires fresh-base PRs and exact-head CI after each mainline merge. The earlier PR heads are not eligible for merge.
- PR #99 contains the decision log and runbook updates; PR #100 contains optional CloudWatch metrics/alarms gated behind `enable_live_twilio`. Neither change proves AWS provisioning, notifications, live Twilio acceptance, or physical capture.
- Keep `TWILIO_ENABLED=false` and release BLOCKED. Engineering completion is not operational/product acceptance.
