# Branch and Pull Request Policy

- Never write directly to main.
- Use one task-scoped branch and one focused PR per independently reviewable outcome.
- Build dependency stacks explicitly; each PR base must be its immediate prerequisite branch.
- Do not rebase, force-push or rewrite a branch that another task depends on.
- Re-check the current base/head SHA before every write and before reporting status.
- CI evidence belongs to the exact commit SHA that ran it.
- The implementer may merge its own PR after exact-head required checks, complete acceptance evidence, resolved material review threads, and current/mergeable branch state. No separate per-PR approval is required when the ruleset requires zero approvals. Do not merge another contributor's PR without explicit authorization; keep auto-merge and governance changes separately owner-authorized.
- Keep feature PRs open until their ancestors are reviewed and integrated in order.
- When changing workflow branch filters, verify the PR's base branch is included; a workflow that never triggers is not a successful check.


## Observed repository configuration (2026-11-28)

The active `protect main` ruleset (ID `27591151`) targets `refs/heads/main` and currently enforces:
- pull requests before merge
- zero required approving reviews (`required_approving_review_count=0`)
- no required last-push approval (`require_last_push_approval=false`)
- no mandatory CODEOWNERS approval (`require_code_owner_review=false`)
- review-thread resolution
- exact required checks: backend PostgreSQL 16/17, Swift Core, iPhone 16 and iPhone 16 Pro XCTest, audio analyzer, Terraform validation, and repository policy
- strict up-to-date checks, deletion protection, non-fast-forward protection, and linear history
- no bypass actors

`require_extra_approval_for_unattributed_changes=true` has no effect while the required approval count is zero, as documented by GitHub. This is a live ruleset observation, not a reason to weaken any required status check or thread-resolution rule.

Recommended policy:
- do not add a blanket approval count for every PR
- keep exact required status checks, strict freshness, review-thread resolution, deletion/non-fast-forward protections, and linear history
- require independent human review only for high/critical-risk changes (credentials, privacy, consent, data loss, security boundaries, or P0/P1)
- allow low/medium-risk changes to use owner-authorized automated self-review and exact-head CI evidence
- do not add broad bypass actors

Do not mutate repository rulesets or branch protection from an agent without explicit owner authorization. First ensure required workflows exist on the default branch and run for every PR targeting it; a required check that is skipped or never created can block all merges.


## Review evidence

A task may record either an actual independent human review or an explicitly owner-authorized automated review. These are distinct evidence modes. High/critical-risk tasks require `independent_human`; low/medium-risk tasks may use `owner_authorized_automated`. Never label automated/self-review as an independent human approval or fabricate a GitHub review. The task validator enforces the risk-based evidence mode. Branch protection, exact-head checks, and required thread resolution are never bypassed.
