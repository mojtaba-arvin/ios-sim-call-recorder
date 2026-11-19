---
name: architecture-review
description: Review proposed changes against repository boundaries, state ownership, lifecycle, concurrency, failure semantics, and documented product pathways.
---

# Architecture review

## Procedure
1. Read AGENTS.md, relevant ADRs and the owning package's architecture docs.
2. Trace the affected call path from public entry point to persistence/provider/UI boundary.
3. Identify state owners, actor isolation, asynchronous suspension points, cancellation and retry behavior.
4. Check whether the change preserves pathway separation: native Phone, external hardware, carrier bridge and app-owned VoIP are distinct.
5. Evaluate failure, recovery, idempotency, retention and deletion semantics.
6. Identify interface changes and downstream consumers before implementation.
7. Check whether a simpler change satisfies the acceptance criteria.
8. Compare docs and tests with the proposed behavior.

## Output
- Boundary diagram or concise call-flow description.
- Invariants and affected interfaces.
- Failure modes and recovery behavior.
- Compatibility and migration implications.
- Blocking findings versus justified trade-offs.

## Completion gate
No unresolved P0/P1 architecture finding; every changed interface has a named owner and validation plan.
