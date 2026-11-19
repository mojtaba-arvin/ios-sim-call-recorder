---
name: evidence-management
description: Maintain traceable, exact-SHA evidence for engineering, platform compatibility, audio quality, device and carrier claims.
---

# Evidence management

## Evidence vocabulary
- static: source/configuration inspection
- unit: isolated deterministic test
- integration: multiple components exercised together
- simulator: simulated OS/runtime, no real telephony proof
- physical-device: exact handset and OS build
- carrier: exact carrier/plan/SIM/network and call scenario

## Procedure
1. Write the claim as a falsifiable statement with a defined scope.
2. Identify the minimum evidence tier that can support it.
3. Record source URL or test artifact, access/run date, exact SHA, environment and method.
4. Separate documented, observed, hypothesis and rejected findings.
5. For device claims, record the complete compatibility tuple and repeat count.
6. For audio claims, assess local and remote speech independently, clipping, gaps, echo, noise and truncation.
7. Keep raw call audio, phone numbers, tokens and personal content out of public artifacts.
8. Revalidate mutable claims before release; stale evidence does not certify current support.
9. Link each product claim to its supporting evidence and list exclusions.

## Output
A claim/evidence register with scope, tier, source, date, exact version/SHA, result, confidence and limitations.

## Completion gate
Every externally visible compatibility claim has evidence at the matching tier; unknown remains unknown.
