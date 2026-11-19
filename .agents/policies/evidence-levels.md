# Evidence Levels

Evidence is scoped to a claim, exact implementation version and environment.

| Tier | Meaning | Can establish | Cannot establish |
|---|---|---|---|
| Static | Source/configuration/document inspection | Declared behavior, structural constraints | Runtime correctness |
| Unit | Isolated deterministic tests | Local logic and invariants | Component integration or OS behavior |
| Integration | Components run together with controlled dependencies | Boundary contracts and persistence interactions | Real carrier/provider behavior unless connected |
| Simulator | iOS Simulator execution | App lifecycle and simulator-visible behavior | Native telephony, accessory behavior or real acoustic capture |
| Physical device | Exact iPhone and iOS build | Device-specific observed behavior | Universal compatibility |
| Carrier | Exact operator, plan, SIM, network and call topology | Combination-specific merge and media behavior | Other carriers/regions/configurations |

## Result labels

- **Confirmed:** repeatable evidence at the required tier supports the claim.
- **Observed:** happened in a bounded test, but repeatability or scope is incomplete.
- **Hypothesis:** plausible and not yet validated.
- **Rejected:** evidence or platform contract rules out the proposed path.

Unknown is not equivalent to unavailable, and a single positive test is not universal support.
