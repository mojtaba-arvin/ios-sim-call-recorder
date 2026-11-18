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