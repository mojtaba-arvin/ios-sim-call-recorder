# Branch and Pull Request Policy

- Never write directly to main.
- Use one task-scoped branch and one focused PR per independently reviewable outcome.
- Build dependency stacks explicitly; each PR base must be its immediate prerequisite branch.
- Do not rebase, force-push or rewrite a branch that another task depends on.
- Re-check the current base/head SHA before every write and before reporting status.
- CI evidence belongs to the exact commit SHA that ran it.
- Do not merge, enable auto-merge or change protection/rulesets without explicit authorization.
- Keep feature PRs open until their ancestors are reviewed and integrated in order.
- When changing workflow branch filters, verify the PR's base branch is included; a workflow that never triggers is not a successful check.


## Observed repository configuration (2026-11-19)

The active repository ruleset named `protect main` targets the default branch and currently enforces only:
- prevent branch deletion
- prevent non-fast-forward updates

The legacy branch-protection endpoint reports `enabled: false`; no required status checks, required pull-request reviews or approval count were configured in the inspected response. This is an observation, not an endorsement.

Recommended next configuration after the workflow foundations are integrated into `main`:
- require pull requests before updating `main`
- require at least one independent approval
- require the exact stable policy, Swift Core and iOS Simulator checks that are actually triggered for main-targeted PRs
- dismiss stale approvals after new commits and require approval of the latest reviewable push
- retain deletion/non-fast-forward protections
- do not add broad bypass actors

Do not mutate repository rulesets or branch protection from an agent without explicit owner authorization. First ensure required workflows exist on the default branch and run for every PR targeting it; a required check that is skipped or never created can block all merges.


## Review evidence

A task may record either an actual independent human review or an explicitly owner-authorized automated review. These are distinct evidence modes. Never label an automated/self-review as an independent human approval, fabricate a GitHub review, or use an owner waiver to bypass branch protection or required human approval. The task validator requires the selected mode and its corresponding evidence.
