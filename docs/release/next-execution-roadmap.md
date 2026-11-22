# Release Readiness Roadmap — Post PR #52

**Status date:** 2026-11-22  
**Release status:** BLOCKED — software foundation and repository CI exist; external acceptance and governance are incomplete.  
**Source of truth at last verified baseline:** `main` at `143b05017fb6eed610951c07e0e272f86d411835` after PR #59. PRs #57, #58 and #59 are merged. A follow-up CI correction is proposed in PR `fix/run-release-preflight-on-main-push-20261122`; it is not merged until its checks pass.

## 0. Latest execution update — 2026-11-22

- PR #59 merged at `143b05017fb6eed610951c07e0e272f86d411835`. Its pre-merge Release Preflight Run `45003000666` passed all eight checks, including XCTest on iPhone 16 and iPhone 16 Pro simulators after runtime provisioning.
- The post-merge commit was checked independently: no workflow run exists for the final main SHA. Root cause confirmed in `.github/workflows/release-preflight.yml`: `push` covered only `release/**`, not `main`.
- A focused follow-up proposes adding `main` to the canonical Release Preflight push branches so merge commits receive the same eight-check gate. This change must pass PR CI before merge; do not report it as active until merged and read back.
- A separate static security review found that the opt-in live Twilio harness accepted arbitrary HTTPS media URLs and unconstrained redirects. PR #61 proposes restricting downloads and redirects to HTTPS AWS S3 endpoints, with regression tests; it does not make provider calls.
- PR #62 corrects consent-event semantics: explicit non-affirmative DTMF is a refusal, while empty Gather and unavailable call outcomes are distinct; generic `CallStatus=completed` is informational. Regression tests and related backend/privacy/counsel documentation are included; CI is pending.
- For PR #60, only a completed run attached to the final PR head counts as validation; canceled runs from superseded commits are not evidence.

- PR #54 merged successfully as `dac0d409388af1623bbebd51306537ad0f842d56`.
- Final pre-merge PR head `7938c89c7053eee2ec0cc9b799f36b489aa9b00f` passed all nine matrix-expanded Release Preflight checks in Run `44995777499`; the separate infrastructure and repository-policy runs `44995777428` and `44995777383` also succeeded.
- Seven logical jobs are defined; PostgreSQL expands to two versions and XCTest to two simulator devices. All nine resulting checks passed on the same final PR head.
- PR #58 merged as `81b5d8c2cdfc947c2f3e2116831f519ab9035d6f`; final head `6766e6113fa7a26aa47a12406e491a1aa7388341` passed all eight Release Preflight checks and the unique Backend Compose lifecycle check (Runs `45000340766` and `45000340755`). The harness is dry-run by default; no live PSTN call has been made.
- PR #57 merged as `fe9748b08c63a3170d33910666fb350b2e1fd6e5`; its final head passed all eight Release Preflight checks (Run `44998126275`) and the unique Backend Compose lifecycle integration (Run `44998126244`).
- Ruleset ID `27591151` remains incomplete: only `deletion` and `non_fast_forward` are active. This connection exposes Ruleset GET but not administrative PUT/PATCH; do not claim governance is fixed.
- Post-merge live branch inventory contains only `main` and the superseded PR #55 branch `feat/twilio-live-acceptance-harness-20261122`. The former PR #53 branch and merged PR #58 branch are already absent.

## 1. Verified baseline

- PR #52 merged at `c236a414ab4e922811cd95004aadc356be5395c3` (159 commits, 60 files).
- PR #52 head: `225e63bb0bef38dfb73dbf5a7a9f7560bc1f4212`.
- Six CI workflows on that head completed successfully: backend/PostgreSQL lifecycle, Swift core, iOS simulator build plus app-hosted XCTest, audio analyzer, Terraform validation, and repository policy.
- These results prove CI execution for that commit only. They do not prove live Twilio account acceptance, physical iPhone/SIM compatibility, AWS staging deployment, legal approval, or production readiness.
- Existing CI workflows are path-filtered and independently dispatched. The new `release-preflight.yml` provides one all-PR release gate and stable job identities.

## 2. Workstream map and PR batches

Workstreams are ordered by release risk. Release Preflight jobs execute concurrently; the two XCTest device jobs each generate/build/test independently, with no serial simulator-build dependency. Backend staging lifecycle remains a separate path-filtered integration check.

| Batch | Workstream | PR scope | Dependency / exit condition |
|---|---|---|---|
| A1 | Governance + CI | `release-preflight.yml`, this roadmap, branch ruleset | CI jobs green; ruleset independently verified |
| A2 | Branch hygiene | Inventory stale refs and classify retention/deletion | No open PR, no deployment/release reference, no unique unmerged work |
| B | Twilio real-account harness | Opt-in staging harness, account/number preflight, consent and callback assertions, evidence bundle; merged implementation in PR #58 | PR #58 merged; credentials and approved test account still required for live acceptance |
| C | Physical iPhone/SIM protocol | Device/operator matrix, repeatable call/merge/import/route tests, evidence template | B is not a prerequisite for native-SIM tests; real devices/SIMs required |
| D | AWS staging | Terraform plan/apply gate, OIDC role, deploy, migration, service health and rollback evidence | A1 merged; AWS account, role, network and staging secrets configured |
| E1 | Security/privacy | Threat-model closure, key/retention/access review, dependency and callback security | B/D evidence available where relevant |
| E2 | Legal/product/operations | Counsel-approved disclosure, jurisdiction/product claims, support/incident/retention runbooks | External counsel and product owner sign-off |

**PR grouping:** A1 is one small CI/documentation PR. Ruleset changes are a separate administrative change, not hidden in a code PR. B, C, D and E are separate PRs or review batches; do not block independent documentation or protocol work on a live provider call.

## 3. Release preflight CI contract

Workflow: `.github/workflows/release-preflight.yml`

| Required job | Execution | Evidence |
|---|---|---|
| `backend-postgres` | PostgreSQL 16/17 matrix, Python 3.13, backend unittest suite | Per-version test log artifact |
| `swift-core` | Swift 6.2 package tests | Swift test log artifact |
| `xctest` | iPhone 16 / iPhone 16 Pro simulator matrix; each job generates the project and builds/tests independently | Per-device log; `.xcresult` retained on failure |
| `audio-analyzer` | WAV analyzer unittest suite | Analyzer log artifact |
| `terraform-validate` | Terraform fmt, backendless init, validate | Job log |
| `repository-policy` | Policy tests, workflow/agent/docs validators | Job log |

Execution controls:
- `pull_request` to `main`, `push` to `main` and `release/**`, and `workflow_dispatch`. The `main` push trigger is proposed in PR #60 and becomes active only after merge.
- Concurrency group per PR/ref with `cancel-in-progress: true`.
- Bounded job timeouts and fail-fast matrices.
- All eight required check identities are produced by the workflow: PostgreSQL 16/17 matrix (two checks), Swift core, XCTest iPhone 16/iPhone 16 Pro matrix (two checks), audio analyzer, Terraform validation and repository policy. Each XCTest matrix job independently generates the project and builds/tests its own simulator destination; there is no separate `ios-sim-build` job.
- Python dependency cache through `setup-python`; test/build outputs uploaded as artifacts with 14-day retention.
- No live Twilio or AWS credentials are used by pull-request jobs. Live provider/deployment operations remain separately gated and opt-in.

## 4. Governance — required administrative state

The currently observed active Ruleset `protect main` (ID `27591151`) targets the default branch but contains only `deletion` and `non_fast_forward` rules. It does **not** currently require PRs, required status checks, or linear history.

Required end state:
1. Require a pull request before merging to `main`.
2. Require the eight stable Release Preflight checks: `backend-postgres (PostgreSQL 16)`, `backend-postgres (PostgreSQL 17)`, `swift-core`, `xctest (iPhone 16)`, `xctest (iPhone 16 Pro)`, `audio-analyzer`, `terraform-validate`, and `repository-policy`. Do not require the path-filtered `Backend staging integration` check globally; it is intentionally absent for unrelated PRs.
3. Require linear history.
4. Restrict force pushes.
5. Keep branch deletion restricted.
6. Do not configure bypass actors for routine development. Preserve only an explicitly documented emergency break-glass policy if organizationally required.

**Verification:** inspect the saved Ruleset after editing and confirm the exact rules, target ref and required-check names. PR #54 historically had nine checks including `ios-sim-build`; PR #57 removed that separate job and established the current eight-check set listed above. Do not require the retired `ios-sim-build` identity. A green workflow is not evidence that branch protection is enabled.

## 5. Branch hygiene inventory

The live branch inventory at this review contains five refs: `main`, `feat/twilio-live-acceptance-harness-20261122`, `fix/run-release-preflight-on-main-push-20261122` (PR #60), `fix/harden-live-harness-media-url-20261122` (PR #61), and `fix/distinguish-consent-decline-from-no-answer-20261122` (PR #62).

| Branch | Evidence | Classification | Action |
|---|---|---|---|
| `main` | Default branch | KEEP | Protected release base |
| `feat/twilio-live-acceptance-harness-20261122` | PR #55 closed/unmerged; no open PR references it. Compared with `main`, the harness script differs only by a one-character formatting/newline delta; README, backend README, harness tests and acceptance protocol are byte-identical. Its roadmap files are older than main. | DELETE CANDIDATE | Superseded by PR #58; retain until tags/deployment references are checked and the ref-deletion action is available |
| `fix/run-release-preflight-on-main-push-20261122` | Open PR #60; contains the `main` push trigger and roadmap reconciliation | KEEP | Active review branch; do not delete before PR #60 is resolved |
| `fix/harden-live-harness-media-url-20261122` | Open PR #61; hardens the opt-in media downloader and adds URL/redirect regression tests | KEEP | Active security review branch; do not delete before PR #61 is resolved |
| `fix/distinguish-consent-decline-from-no-answer-20261122` | Open PR #62; distinguishes explicit refusal from unavailable participants and aligns consent documentation | KEEP | Active consent-correctness review branch; do not delete before PR #62 is resolved |

Do not invent historical branch names. The PR #55 branch is 12 commits ahead and 3 behind by ancestry because the replacement PR was squash-merged; compare its actual file content before deletion. Current code/test/acceptance files are present on `main`; roadmap differences are stale historical text, not new implementation. Tags/deployment references were not verified through the available connector, and the connector exposes no ref-deletion action. Branch deletion is not a release gate and must not delay A1/B/C/D.

## 6. Release blockers — measurable actions

| Blocker | Action | Owner role | Acceptance criteria | CI / evidence |
|---|---|---|---|---|
| Governance incomplete | Apply the six governance requirements above | Repository admin | Ruleset read-back confirms PR, required checks, linear history, force-push restriction and deletion restriction | Ruleset JSON/screenshot + PR checks |
| CI gate optimization | PR #57 is merged; keep Release Preflight and unique Backend Compose lifecycle green on relevant PRs | CI owner | All eight matrix-expanded Release Preflight checks green on the same commit; Backend integration green when backend/Compose paths change | Actions run URLs + artifact IDs |
| Twilio unverified | Use `backend/tools/twilio_live_acceptance.py` (PR #58) in staging only; run consent accept/decline/no-answer, Conference lifecycle, recording-from-start, callback signature/account scope, retrieval, dual-channel validation and retention deletion | Backend/provider owner | Every scenario has expected terminal state; no cross-account callback acceptance; evidence includes sanitized call/Conference/Recording SIDs and timestamps | Manual workflow run, sanitized logs, test matrix; no secrets or phone numbers |
| Native SIM route unverified | Execute physical protocol on declared iPhone/iOS/carrier/SIM combinations; distinguish native SIM merge from app-owned Twilio Conference | iOS/device QA owner | Repeated runs per combination; record call topology, merge availability, import path, audio integrity, channel attribution, interruptions and failure modes | Signed device matrix, screen/video evidence where lawful, imported test files and analyzer report |
| AWS staging unverified | Provision staging with Terraform, OIDC, encrypted storage, migrations, API/worker/retention services, readiness and rollback | Cloud/platform owner | Deploy exact commit SHA; migration exit 0; ECS services stable; readiness passes; KMS/S3 access and retention deletion verified | Terraform plan/apply output, deployment run, ECS task/service output, health response, rollback record |
| Security/privacy review open | Review tenant isolation, callback auth, address encryption, logs, object lifecycle, IAM/KMS and data deletion | Security owner | Threat-model findings dispositioned; no secrets/PII in logs; key/retention controls demonstrated | Review checklist, policy tests, sanitized audit and deletion evidence |
| Legal approval open | Obtain jurisdiction-specific consent/disclosure and recording-law review; verify App Store/product claims | Legal counsel + product owner | Written counsel approval and approved disclosure copy; product wording does not claim universal native SIM recording | Signed legal decision and approved copy |
| Operations incomplete | Validate incident, failed-call, callback retry, queue recovery, retention and support runbooks | Operations owner | Each critical failure has detection, owner, recovery and evidence path | Runbook drill record and sanitized operational logs |

## 7. Execution policy / timeboxes

- A1 CI and governance read-back: one focused implementation/review cycle; CI jobs have 5–30 minute hard timeouts.
- B Twilio harness: PR #58 merged a dry-run-by-default script with mandatory `--execute`, `BRIDGE_ENVIRONMENT=staging`, a staging host and `TWILIO_LIVE_TEST_APPROVED=true`; first perform zero-cost configuration/preflight; live PSTN scenarios only on the approved test account and explicit manual dispatch.
- C physical tests: batch by device/iOS/carrier and execute all independent combinations in one lab session; do not infer support from simulator results.
- D AWS: run plan and static checks in CI first; perform apply/deploy only in the protected staging environment.
- E security/legal/product/ops: parallel document reviews; legal approval is a hard release gate, not a coding task.
- Stop and report the first failing gate with its run URL/log/artifact. Do not rerun successful jobs unnecessarily.
- Never label a test, benchmark, live call, deployment, legal review or device combination Passed without a durable artifact or signed external evidence.
- Release remains blocked until all release-critical rows in section 6 are accepted.


## Latest verified execution — 2026-11-22 (after PRs #60–#62)

**Current main:** `9f59fecd7a79834437ef57bee1488fd6b7991797` (PR #61 merge). PRs #60, #61 and #62 are merged. There are no open pull requests at this snapshot.

- PR #60 enabled the canonical Release Preflight on pushes to `main` as well as PRs and release branches. Its first mainline run on the #62 merge SHA (`45006994080`) was superseded/cancelled when the next main push arrived; four completed jobs passed and the two XCTest jobs were cancelled. Do not count that run as a full pass.
- PR #61 hardened the opt-in live Twilio acceptance harness: media retrieval and redirect targets are restricted to approved HTTPS AWS S3 endpoint forms. Final PR-head Release Preflight `45006749306` passed all 8 jobs and backend staging integration `45006749375` passed. Merged as `9f59fecd7a79834437ef57bee1488fd6b7991797`.
- PR #62 distinguishes explicit non-affirmative DTMF refusal from no-answer/busy/failed/canceled/unanswered outcomes. Generic `CallStatus=completed` is informational and cannot override authoritative Gather consent. Final PR-head Release Preflight `45004464750` passed all 8 jobs and backend staging integration `45004464735` passed. Merged as `46e44bc7f2b18b998e13cc519bce110e09ad0d10`.
- **Latest mainline verification:** Release Preflight run `45007294450` on exact current main SHA `9f59fecd7a79834437ef57bee1488fd6b7991797` completed with conclusion `success`; all 8 jobs passed: PostgreSQL 16, PostgreSQL 17, Swift core, XCTest iPhone 16, XCTest iPhone 16 Pro, audio analyzer, Terraform validate and repository policy. This is simulator/software CI evidence only.
- The previous mainline run `45006994080` completed as `cancelled` due to superseding push, not as a test failure and not as a full pass.
- Active Ruleset `protect main` (ID `27591151`) was read back again. It is active, targets `~DEFAULT_BRANCH`, has empty bypass actors, and still contains only `deletion` and `non_fast_forward`. It does **not** require PRs, the eight status checks, or linear history. The branch API reports `main` protected, but this does not establish that the required rules are configured. The connected GitHub actions expose ruleset reads but no ruleset administrative write action.
- Live branch inventory contains only `main` and stale branch `feat/twilio-live-acceptance-harness-20261122` at `834d8b91a30c547e67739cbe370bc2b46e0738a7`. PR #55 is closed/unmerged and the branch is superseded by merged PR #58. No branch-ref deletion action is exposed by the current GitHub connection; retain this as an admin/branch-cleanup action rather than claiming deletion.
- PR #56 remains open to track the privileged Ruleset update. It is not closed because the required administrative state has not been applied and verified.

### Current release decision

**Release remains BLOCKED.** The green mainline run proves the current repository software gates, not production readiness. Remaining independent gates are:

1. Privileged update and read-back of Ruleset #27591151: require PRs, all eight stable Release Preflight checks, linear history, force-push restriction, deletion restriction and no routine bypass actors.
2. Select and document one launch jurisdiction and intended product mode; obtain counsel approval for disclosure, lawful basis, vendor/data-transfer terms, retention and user rights. Keep `TWILIO_ENABLED=false` until approved.
3. Perform the opt-in staging Twilio acceptance only after the safety contract is satisfied: two authorized test participants, approved disclosure, dedicated staging account/numbers, spending cap, signed callbacks, positive consent, explicit refusal, no-answer, cancellation, media validation and independent Twilio/S3 deletion verification.
4. Provision AWS staging only after account/role/secrets/network/certificate ownership and a reviewed costed Terraform plan are available; then deploy, migrate, health-check and execute rollback evidence. No AWS resources have been applied.
5. Run physical iPhone/SIM/carrier/accessory tests for any native-call pathway claim. At least three repeats establish bounded feasibility only; the documented production-support threshold remains at least 20 consecutive successful core runs plus interruption/route-change scenarios. No physical-device or carrier acceptance is currently established.
6. Complete customer discovery, paid-pilot evidence, unit economics, support/incident readiness and App Store review before commercial release.

**Product boundary remains unchanged:** the Twilio route is an app-owned outbound two-party Conference, not capture or merge of an existing native SIM call and not access to Phone.app private audio. The companion/import path is the safe interim product mode while provider/legal gates remain closed.
