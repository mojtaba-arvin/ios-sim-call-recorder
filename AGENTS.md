# Agent Engineering Contract

This repository may be changed by humans, coding agents, automated workflows and external contributors. These rules apply to all of them.

## Non-negotiable invariants

1. Never commit or push directly to `main`. Work on a task-scoped branch and submit a pull request.
2. Never force-push or rewrite shared history. The implementer may merge its own PR after exact-head required checks pass, acceptance evidence is complete, material review threads are resolved, and the branch is current and mergeable; no separate per-PR approval is required when the ruleset requires zero approvals. Never merge another contributor's PR without explicit authorization or change repository governance settings without owner authorization.
3. Never claim a feature, test, benchmark, device compatibility result or security property without reproducible evidence.
4. Never implement native cellular-call interception through private APIs or imply that CallKit grants access to the Phone app's audio.
5. Recording must fail closed when the required participant consent cannot be verified.
6. Do not store secrets, personal call content, raw phone numbers or unredacted provider payloads in source control, test fixtures or ordinary logs.
7. A successful build is not proof of physical-device behavior. Label simulator, unit, integration, carrier and physical-device evidence separately.

## Task lifecycle

Every non-trivial task follows this sequence:

1. **Discover:** read this file, relevant package instructions, open issues, active PRs, branch state and existing architecture decisions. Inspect the relevant commit/PR history and failed CI runs for repeated corrections or stale assumptions.
2. **Scope:** write the intended outcome, acceptance criteria, affected paths, risks and explicit non-goals before editing.
3. **Isolate:** create one task branch from the current intended base. Do not let concurrent agents edit the same branch or files.
4. **Implement:** make the smallest coherent change. Preserve adapter boundaries and backwards compatibility where practical.
5. **Verify:** run a preflight before the first commit where the local toolchain permits it, then focused tests, full relevant tests, static checks and security checks. Independently validate generated fixtures before using them. Record exact commands, toolchain versions and results.
6. **Review:** inspect the final diff as a reviewer, not only as the author. Check error paths, cancellation, actor reentrancy, concurrency, privacy and stale documentation.
7. **Publish:** open/update a PR with evidence, limitations, risks and linked issues. Keep it unmerged until exact-head required checks and the risk-based review requirement are satisfied. Low/medium-risk changes may use an explicitly owner-authorized automated self-review; high/critical-risk changes require an actual independent human review.
8. **Report:** re-read the current PR head SHA and state it with the PR URL, checks and remaining uncertainty. Inspect job steps and test summaries. A passing run on an earlier SHA, or a queued/pending/cancelled/skipped run, is not a pass. Never equate a build with a test pass.

## Agent roles and skills

Role contracts live in `.agents/roles/`; reusable, task-oriented skills live in `.agents/skills/<skill-name>/SKILL.md`. Before a task, select the relevant role and skills rather than copying generic instructions into each issue.

- Roles define responsibility, authority boundaries and deliverables.
- Skills define repeatable procedures, inputs, outputs and completion gates.
- Templates in `.agents/templates/` define task, ADR, research-report, independent PR-review and validation-report structure.
- Policies in `.agents/policies/` are the canonical privacy, branch and evidence rules.
- `scripts/validate_agent_assets.py` checks required role/skill/template/policy structure; it does not prove that an agent executed a skill correctly.
- `scripts/validate_agent_tasks.py` checks machine-readable task contracts, dependency existence/cycles and done-state evidence fields; it does not query GitHub or execute work.

## Multi-agent work allocation

Use the role contracts in `.agents/roles/`. Each task has one accountable implementer. Require a separate independent reviewer for high/critical-risk work; low/medium-risk work may use owner-authorized automated self-review when no independent reviewer is available.

- Parallelize only work with disjoint path ownership and explicit interfaces.
- Assign a file/path ownership list to each worker before execution.
- A worker must not modify files outside its assignment without coordination.
- Shared branches are not shared workspaces: do not have multiple agents commit to the same branch concurrently.
- Integrate work through separate branches/PRs or sequential cherry-picks after validation.
- The reviewer must inspect the actual diff and test evidence; it must not rely on the implementer's summary.
- Record review evidence honestly: an independent human review and an owner-authorized automated review are different modes. Never claim an automated review was an independent human approval or fabricate a GitHub review.
- If no independent agent runtime is available, do not pretend one was spawned. Execute the role separation sequentially and document that limitation.

## Git policy

- Branch names: `feat/*`, `fix/*`, `docs/*`, `research/*`, `test/*`, `chore/*`.
- Commit messages follow Conventional Commits: `type(scope): imperative summary`.
- Keep commits focused; do not mix unrelated research, code and governance changes.
- Never commit generated build products, credentials, provisioning profiles, signing keys, recordings or personally identifiable test data.
- PRs target `main`, describe behavior and risk, link issues, and include test evidence.
- Rebase/merge updates only when the branch owner controls the branch and no other worker is using it. Never force-push shared branches.
- Do not enable auto-merge unless repository rules enforce all required checks and the user explicitly authorizes it.
- Do not merge merely because GitHub reports `mergeable: true`.

## CI and quality gates

- Workflows use least-privilege permissions, explicit job timeouts and immutable full-length commit SHAs for third-party actions.
- CI must be deterministic, run the required PR checks consistently, and avoid cancelling unrelated jobs. Do not use path filters on checks that are configured as required status checks.
- Required checks must correspond to stable job names.
- A check is passed only when the exact current PR head SHA has a completed successful run.
- A skipped workflow is not a passing check unless the ruleset intentionally makes that workflow optional for the changed paths.
- Any workflow change must itself be reviewed for token permissions, untrusted PR code, injection, artifact exposure and supply-chain risk.

## Recording-specific engineering

- Pathway adapters are independent. Failure or unavailability of one pathway must not prevent discovery of others.
- Capability decisions are scoped to an exact compatibility tuple.
- Consent evidence must be verified by a trusted component; a non-empty string supplied by a caller is not proof of consent.
- A media artifact is not complete merely because a provider returned a URL or file.
- Verify local and remote audio independently. One-sided or malformed artifacts are degraded, never successful.
- Every provider webhook must be authenticated, replay-safe, idempotent and privacy-redacted.
- Experimental, jailbreak and private-API work remains isolated from production/App Store targets.

## Completion definition

A task is complete only when its acceptance criteria are met, relevant checks pass on the final commit, the diff and risks are reviewed, documentation is accurate, and the PR is mergeable. High/critical-risk tasks additionally require an actual independent human review; routine low/medium-risk tasks do not wait for a blanket human approval.
