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
