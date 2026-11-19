# Agent Workflow and Coordination

## Default topology

```text
Product owner / task requester
          |
          v
   Product / architecture
          |
          +----> Research (evidence + compatibility)
          |
          +----> Implementation (one scoped branch)
          |
          +----> Independent review (read-only until findings)
          |
          v
   CI / physical-device validation
          |
          v
   PR ready for human review
```

## Work item contract

Each issue should identify:
- user/product outcome
- acceptance criteria that can be observed
- in-scope and out-of-scope paths
- dependencies and interface contracts
- risk class: low, medium, high, critical
- required validation tier: static, unit, integration, simulator, physical device, carrier
- rollback or failure behavior
- evidence expected in the PR

## Parallel execution rules

Parallel workers must have disjoint path ownership. If two work items need the same interface, the architect defines the interface first; implementation proceeds after the contract is committed. Avoid speculative branches that cannot be integrated independently.

## Historical learning and preflight

Before implementing a non-trivial change:

1. Inspect relevant commit history, previous PR review comments and failed CI runs. Identify repeated corrections, branch-filter omissions, stale documentation and test-fixture assumptions before choosing an approach.
2. Turn those findings into explicit acceptance criteria and preflight checks. Do not repeat a known failure merely because it was fixed in a later commit.
3. Run cheap deterministic checks before the first commit: project generation, formatting/static validation, focused tests and the relevant build/test command when the local toolchain supports it.
4. Batch related changes into coherent reviewable commits. Avoid a chain of speculative commits that each fix a predictable issue; preserve separate commits when they represent independently reviewable outcomes.
5. When generating media or other test fixtures, validate the fixture independently before passing it to production code. Reopen/decode generated media and assert its metadata, duration and format.
6. Treat documentation claims about CI, compatibility, security or performance as evidence-bearing statements. Use exact commit/run scope for mutable CI status; never write an unconditional "CI passes" claim based on an older or partial run.

## Review gates

- P0: credentials, privacy, consent bypass, data loss, direct main mutation — block immediately.
- P1: lifecycle correctness, race conditions, concurrency, incorrect compatibility claims, missing critical tests — block merge.
- P2: maintainability, observability, documentation and performance concerns — fix or explicitly justify.
- P3: style-only improvements — do not block a release unless they obscure correctness.

## Evidence vocabulary

- `static`: source inspection or linter only
- `unit`: isolated deterministic tests
- `integration`: components exercised together with controlled dependencies
- `simulator`: iOS simulator, not physical telephony
- `physical-device`: exact device and OS build
- `carrier`: exact operator, plan, SIM and call scenario

Do not promote evidence from one tier to another.

## Exact-head validation

- Query the current PR head SHA immediately before reporting completion.
- A passing run on an earlier commit does not validate the current PR head.
- Inspect job steps and test summaries; distinguish setup, build, test execution and test success.
- If a later documentation-only or metadata-only commit changes the PR head, either obtain fresh required checks or clearly state that the latest validation belongs to the previous code SHA.
- A queued, pending, cancelled or skipped run is not a pass.
