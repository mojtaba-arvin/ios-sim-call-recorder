# ADR-0001: Separate call-capture pathways behind adapters

- Status: Accepted as an architectural direction; implementation deferred until a pathway passes a physical-device proof.
- Date: 2026-11-19

## Context

The project investigates materially different mechanisms: native iOS companion workflows, carrier conference bridges, carrier recording services, app-owned VoIP, external accessories and isolated experimental techniques. They have different permissions, reliability, distribution constraints and compatibility dimensions. A single capture implementation or UI coupled to one mechanism would make parallel research and future replacement unnecessarily expensive.

## Decision

Use a pathway adapter boundary coordinated by a recording orchestrator.

Each adapter must expose:
- a capability assessment for the current device, OS, region, carrier and route where that information is available;
- explicit prerequisites and user-facing limitations;
- a session lifecycle with typed failure and interruption states;
- consent/disclosure requirements;
- evidence metadata identifying the exact tested compatibility tuple.

The orchestrator owns lifecycle and UI-facing state. Adapters own pathway-specific behavior. Backend and accessory components remain separate deployable systems where required.

## Consequences

Positive:
- Research tracks can proceed independently.
- Experimental approaches can remain isolated from production targets.
- A pathway can be disabled by capability without destabilizing others.
- Compatibility claims can be attached to explicit configurations.

Costs:
- More interfaces and test doubles are required.
- Capability detection may be incomplete or carrier-dependent.
- The orchestrator must handle partial support and degraded outcomes honestly.

## Non-goals

This decision does not assert that iOS exposes native cellular call audio to third-party apps. It does not select a final capture mechanism, guarantee App Store approval, or claim universal iPhone support.

## Revisit when

A pathway passes the acceptance gates in the research matrix, or new public Apple APIs materially change the platform boundary.
