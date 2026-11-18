## Outcome
<!-- What user/product outcome does this change deliver? -->

## Change type
- [ ] Feature
- [ ] Fix
- [ ] Research
- [ ] Documentation
- [ ] CI / tooling
- [ ] Refactor

## Scope
- [ ] Scope is limited to the linked issue/task.
- [ ] No unrelated refactors or generated artifacts are included.
- [ ] Public interfaces and architecture decisions are documented where needed.

## Agent / contributor ownership
- Implementer:
- Reviewer:
- Validator:
- Assigned paths:
- Parallel work and interface contract:

## Technical approach
<!-- Explain the approach, alternatives considered and relevant architecture decisions. -->

## Evidence and compatibility
- Device / hardware identifier:
- iOS version and exact build:
- Device region / physical test country / language:
- Carrier / plan / carrier bundle:
- SIM configuration / roaming / network:
- Call scenario / audio route:
- Pathway ID / app / backend / firmware version:
- Repeat count and result:

Mark every claim as **confirmed**, **observed**, **hypothesis**, or **rejected**. For documentation-only or non-device changes, state "not applicable"; never imply physical-device validation.

## Validation evidence
| Tier | Command / environment | Result | Exact commit SHA |
|---|---|---|---|
| Static | | | |
| Unit | | | |
| Integration | | | |
| Simulator | | | |
| Physical device / carrier | | | |

## Safety, risk and rollback
- [ ] Consent and privacy boundaries preserved.
- [ ] No secrets, recordings, raw phone numbers or personal data committed.
- [ ] Error, retry, interruption and cancellation paths considered.
- [ ] Workflow permissions and action pinning reviewed if CI changed.
- [ ] Compatibility and distribution claims match the evidence scope.
- Known limitations:
- Rollback plan:

## Completion checklist
- [ ] Read AGENTS.md and relevant ADRs.
- [ ] Tests pass on the exact PR head.
- [ ] Final diff independently reviewed.
- [ ] Linked issue(s) and updated documentation.
- [ ] No direct main mutation or force-push.
