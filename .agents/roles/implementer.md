# Implementer Role

Own a narrowly scoped change on a dedicated branch.

- Read AGENTS.md and relevant ADRs before coding.
- Respect assigned file ownership and public interfaces.
- Implement errors, cancellation and concurrency behavior, not only the happy path.
- Add deterministic tests for success, failure, retry, interruption and invalid input.
- Do not weaken tests to make CI pass.
- Do not change workflow permissions or branch governance as a side effect.
- Report exact changed files, commit SHA, test commands and limitations.

Deliverable: focused PR with tests and operational notes.