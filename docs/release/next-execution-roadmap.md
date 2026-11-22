# Release Readiness Roadmap — Post PR #52

**Status date:** 2026-11-22  
**Release status:** BLOCKED — software foundation and repository CI exist; external acceptance and governance are incomplete.  
**Source of truth:** `main` at `fe9748b08c63a3170d33910666fb350b2e1fd6e5` after PR #57 (which includes PR #54 and the PR #52 baseline). PR #58 is the only open implementation PR; its final-head CI is green, but it has not yet been merged.

## 0. Latest execution update — 2026-11-22

- PR #54 merged successfully as `dac0d409388af1623bbebd51306537ad0f842d56`.
- Final pre-merge PR head `7938c89c7053eee2ec0cc9b799f36b489aa9b00f` passed all nine matrix-expanded Release Preflight checks in Run `44995777499`; the separate infrastructure and repository-policy runs `44995777428` and `44995777383` also succeeded.
- Seven logical jobs are defined; PostgreSQL expands to two versions and XCTest to two simulator devices. All nine resulting checks passed on the same final PR head.
- PR #55 contains the opt-in Twilio real-account acceptance harness, safety-guard unit tests and operator protocol. The harness is dry-run by default; no live PSTN call has been made.\n- PR #57 merged as `fe9748b08c63a3170d33910666fb350b2e1fd6e5`; its final head passed all eight Release Preflight checks (Run `44998126275`) and the unique Backend Compose lifecycle integration (Run `44998126244`).
- Ruleset ID `27591151` remains incomplete: only `deletion` and `non_fast_forward` are active. This connection exposes Ruleset GET but not administrative PUT/PATCH; do not claim governance is fixed.
- Branch inventory must be refreshed after the merge. PR #53 remains closed/unmerged, but its branch has no remaining file delta against current `main`; the branch is safe to remove.

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
| B | Twilio real-account harness | Opt-in staging harness, account/number preflight, consent and callback assertions, evidence bundle; implementation in PR #58 | PR #58 CI green; credentials and approved test account available |
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
| `ios-sim-build` | XcodeGen, privacy manifest lint, simulator build | Build log and app artifact |
| `xctest` | iPhone 16 / iPhone 16 Pro simulator matrix; each job generates the project and builds/tests independently | Per-device log; `.xcresult` retained on failure |
| `audio-analyzer` | WAV analyzer unittest suite | Analyzer log artifact |
| `terraform-validate` | Terraform fmt, backendless init, validate | Job log |
| `repository-policy` | Policy tests, workflow/agent/docs validators | Job log |

Execution controls:
- `pull_request` to `main`, `push` to `release/**`, and `workflow_dispatch`.
- Concurrency group per PR/ref with `cancel-in-progress: true`.
- Bounded job timeouts and fail-fast matrices.
- Independent jobs run in parallel; XCTest alone depends on `ios-sim-build`.
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

**Verification:** inspect the saved Ruleset after editing and confirm the exact rules, target ref and required-check names. The required matrix-expanded check identities observed on PR #54 were `backend-postgres (PostgreSQL 16)`, `backend-postgres (PostgreSQL 17)`, `swift-core`, `ios-sim-build`, `xctest (iPhone 16)`, `xctest (iPhone 16 Pro)`, `audio-analyzer`, `terraform-validate`, and `repository-policy`. A green workflow is not evidence that branch protection is enabled.

## 5. Branch hygiene inventory

The current live branch inventory contains exactly four refs: `main`, `chore/cross-repo-engineering-baseline`, `feat/twilio-live-acceptance-harness-20261122`, and `feat/twilio-live-acceptance-harness-mainline-20261122`.

| Branch | Evidence | Classification | Action |
|---|---|---|---|
| `main` | Default branch | KEEP | Protected release base |
| `chore/cross-repo-engineering-baseline` | PR #53 is closed, not merged; compare against current `main` reports no changed files; no open PR | DELETE | No remaining file delta or active PR dependency |\n| `feat/twilio-live-acceptance-harness-20261122` | PR #55 closed, not merged; diverged from `main` (12 ahead / 1 behind); superseded by PR #58 | DELETE | Its implementation and reconciled roadmap changes are carried by PR #58 |\n| `feat/twilio-live-acceptance-harness-mainline-20261122` | Active PR #58; 8 commits ahead, 0 behind; final-head CI green | KEEP UNTIL MERGE | Merge PR #58, then delete the merged head branch |

Do not invent four additional branch names. Re-run the branch inventory before deletion and compare every candidate against open PRs, tags, deployments and unique commits. Branch deletion is not a release gate and must not delay A1/B/C/D.

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
- B Twilio harness: PR #58 adds a dry-run-by-default script with mandatory `--execute`, `BRIDGE_ENVIRONMENT=staging`, a staging host and `TWILIO_LIVE_TEST_APPROVED=true`; first perform zero-cost configuration/preflight; live PSTN scenarios only on the approved test account and explicit manual dispatch.
- C physical tests: batch by device/iOS/carrier and execute all independent combinations in one lab session; do not infer support from simulator results.
- D AWS: run plan and static checks in CI first; perform apply/deploy only in the protected staging environment.
- E security/legal/product/ops: parallel document reviews; legal approval is a hard release gate, not a coding task.
- Stop and report the first failing gate with its run URL/log/artifact. Do not rerun successful jobs unnecessarily.
- Never label a test, benchmark, live call, deployment, legal review or device combination Passed without a durable artifact or signed external evidence.
- Release remains blocked until all release-critical rows in section 6 are accepted.
