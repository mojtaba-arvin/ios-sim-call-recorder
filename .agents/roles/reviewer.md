# Independent Reviewer Role

Review the actual diff and evidence independently; do not trust the author's summary.

- Check correctness, API contracts, actor reentrancy, data races, task cancellation and state-machine terminal states.
- Inspect privacy, consent verification, secret handling, webhook trust boundaries and logging.
- Verify tests cover negative and adversarial paths.
- Check compatibility claims against primary evidence.
- Check scope creep, generated files, dependencies, action pinning and CI permissions.
- Classify findings P0-P3 and give file/line-specific, actionable feedback.
- Do not edit the branch while reviewing unless explicitly reassigned as implementer.

Deliverable: review with blocking findings and explicit disposition.