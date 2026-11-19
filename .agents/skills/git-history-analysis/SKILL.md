---
name: git-history-analysis
description: Analyze repository commit history, PR dependencies, review feedback, and failed CI to prevent recurring engineering mistakes before implementation.
---

# Git history analysis

## Inputs
- Repository and target branch.
- Task scope, relevant paths, open PRs and known failure symptoms.

## Procedure
1. Identify the target branch head and task base SHA.
2. Inspect commits touching the target paths and summarize behavioral changes, not only commit messages.
3. Inspect open PRs that modify the same paths and construct the dependency order.
4. Inspect review comments and prior revisions for rejected approaches and repeated corrections.
5. Inspect failed/cancelled workflow runs on relevant commits; read job steps/logs to distinguish setup, build, test and infrastructure failures.
6. Compare the current implementation with the last known-good state where practical.
7. Convert each applicable lesson into a preflight check or acceptance criterion.
8. Record what was not inspected and avoid inferring intent from commit titles alone.

## Output
- Base/head SHAs and relevant commit/PR links.
- Dependency graph and overlapping file ownership.
- Repeated failure patterns with exact run/commit references.
- Preventive checks for the current task.
- Unresolved history gaps.

## Completion gate
No implementation begins until the intended base, relevant dependencies and known recurring failures are explicit.
