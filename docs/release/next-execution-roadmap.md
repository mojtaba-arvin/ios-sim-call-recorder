# Release Readiness Roadmap — Post PR #52

**Status date:** 2026-11-22  
**Release status:** BLOCKED — software foundation and repository CI exist; external acceptance and governance are incomplete.  
**Source of truth:** `main` after PR #54 (which includes the PR #52 baseline). PR #53 is closed and **not merged**; none of its content is assumed to exist on `main`.

## 1. Verified baseline

- PR #52 merged at `c236a414ab4e922811cd95004aadc356be5395c3` (159 commits, 60 files).
- PR #52 head: `225e63bb0bef38dfb73dbf5a7a9f7560bc1f4212`.
- Six CI workflows on that head completed successfully: backend/PostgreSQL lifecycle, Swift core, iOS simulator build plus app-hosted XCTest, audio analyzer, Terraform validation, and repository policy.
- These results prove CI execution for that commit only. They do not prove live Twilio account acceptance, physical iPhone/SIM compatibility, AWS staging deployment, legal approval, or production readiness.
- Existing CI workflows are path-filtered and independently dispatched. The new `release-preflight.yml` provides one all-PR release gate and stable job identities.

## 2. Workstream map and PR batches

Workstreams are ordered by release risk. Release Preflight jobs execute concurrently; the two XCTest device jobs each build and test independently, with no serial simulator-build dependency. Backend staging lifecycle remains a separate path-filtered integration check.

| Batch | Workstream | PR scope | Dependency / exit condition |
|---|---|---|---|
| A1 | Governance + CI | `release-preflight.yml`, this roadmap, branch ruleset | CI jobs green; ruleset independently verified |
| A2 | Branch hygiene | Inventory stale refs and classify retention/deletion | No open PR, no deployment/release reference, no unique unmerged work |
| B | Twilio real-account harness | Opt-in staging harness, account/number preflight, consent and callback assertions, evidence bundle | A1 merged; credentials and approved test account available |
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
| `xctest` | iPhone 16 / iPhone 16 Pro simulator matrix; depends only on simulator build | XCTest log and .xcresult artifact |
| `audio-analyzer` | WAV analyzer unittest suite | Analyzer log artifact |
| `terraform-validate` | Terraform fmt, backendless init, validate | Job log |
| `repository-policy` | Policy tests, workflow/agent/docs validators | Job log |

Execution controls:
- `pull_request` to `main`, `push` to `release/**`, and `workflow_dispatch`.
- Concurrency group per PR/ref with `cancel-in-progress: true`.
- Bounded job timeouts and fail-fast matrices.
- All Release Preflight jobs run independently in parallel; no serial iOS build gate. The device matrix provides two parallel build-and-test jobs.
- Python dependency cache through `setup-python`; compact test logs upload on completion, while large XCTest result bundles upload only on failure (14-day retention).
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

**Verification:** inspect the saved Ruleset after editing and confirm the exact rules, target ref and required-check names. A green workflow is not evidence that branch protection is enabled.

## 5. Branch hygiene inventory

The live branch search returned only `main` and `chore/cross-repo-engineering-baseline`; a follow-up page returned no further branches. This does not substantiate a five-branch deletion list.

| Branch | Evidence | Classification | Action |
|---|---|---|---|
| `main` | Default branch | KEEP | Protected release base |
| `chore/cross-repo-engineering-baseline` | PR #53 is closed, not merged; PR metadata reports 0 changed files / 0 additions / 0 deletions | DELETE CANDIDATE | Verify no open PR, no unique commits needed, then delete |

Do not invent four additional branch names. Re-run the branch inventory before deletion and compare every candidate against open PRs, tags, deployments and unique commits. Branch deletion is not a release gate and must not delay A1/B/C/D.

## 6. Release blockers — measurable actions

| Blocker | Action | Owner role | Acceptance criteria | CI / evidence |
|---|---|---|---|---|
| Governance incomplete | Apply the six governance requirements above | Repository admin | Ruleset read-back confirms PR, required checks, linear history, force-push restriction and deletion restriction | Ruleset JSON/screenshot + PR checks |
| CI lacks one release gate | Merge and run release preflight | CI owner | All eight matrix-expanded Release Preflight checks green on the same commit; compact logs retained and failure bundles available | Actions run URL + artifact IDs |
| Twilio unverified | Add opt-in real-account harness; run consent accept/decline/no-answer, Conference lifecycle, recording-from-start, callback signature/account scope, retrieval, dual-channel validation and retention deletion | Backend/provider owner | Every scenario has expected terminal state; no cross-account callback acceptance; evidence includes sanitized call/Conference/Recording SIDs and timestamps | Manual workflow run, sanitized logs, test matrix; no secrets or phone numbers |
| Native SIM route unverified | Execute physical protocol on declared iPhone/iOS/carrier/SIM combinations; distinguish native SIM merge from app-owned Twilio Conference | iOS/device QA owner | Repeated runs per combination; record call topology, merge availability, import path, audio integrity, channel attribution, interruptions and failure modes | Signed device matrix, screen/video evidence where lawful, imported test files and analyzer report |
| AWS staging unverified | Provision staging with Terraform, OIDC, encrypted storage, migrations, API/worker/retention services, readiness and rollback | Cloud/platform owner | Deploy exact commit SHA; migration exit 0; ECS services stable; readiness passes; KMS/S3 access and retention deletion verified | Terraform plan/apply output, deployment run, ECS task/service output, health response, rollback record |
| Security/privacy review open | Review tenant isolation, callback auth, address encryption, logs, object lifecycle, IAM/KMS and data deletion | Security owner | Threat-model findings dispositioned; no secrets/PII in logs; key/retention controls demonstrated | Review checklist, policy tests, sanitized audit and deletion evidence |
| Legal approval open | Obtain jurisdiction-specific consent/disclosure and recording-law review; verify App Store/product claims | Legal counsel + product owner | Written counsel approval and approved disclosure copy; product wording does not claim universal native SIM recording | Signed legal decision and approved copy |
| Operations incomplete | Validate incident, failed-call, callback retry, queue recovery, retention and support runbooks | Operations owner | Each critical failure has detection, owner, recovery and evidence path | Runbook drill record and sanitized operational logs |

## 7. Execution policy / timeboxes

- A1 CI and governance read-back: one focused implementation/review cycle; CI jobs have 5–30 minute hard timeouts.
- B Twilio harness: first perform zero-cost configuration/preflight; live PSTN scenarios only on the approved test account and explicit manual dispatch.
- C physical tests: batch by device/iOS/carrier and execute all independent combinations in one lab session; do not infer support from simulator results.
- D AWS: run plan and static checks in CI first; perform apply/deploy only in the protected staging environment.
- E security/legal/product/ops: parallel document reviews; legal approval is a hard release gate, not a coding task.
- Stop and report the first failing gate with its run URL/log/artifact. Do not rerun successful jobs unnecessarily.
- Never label a test, benchmark, live call, deployment, legal review or device combination Passed without a durable artifact or signed external evidence.
- Release remains blocked until all release-critical rows in section 6 are accepted.
