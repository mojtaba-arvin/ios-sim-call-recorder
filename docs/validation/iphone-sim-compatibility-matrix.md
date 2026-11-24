# iPhone / SIM Compatibility Matrix

**Status:** execution template only — no physical-device results are recorded here.  
**Related:** Issue #18; [physical-device protocol](../engineering/physical-device-test-protocol.md); [remote validation kit](remote-device-validation-kit.md).

## Rules

- One matrix row represents one exact compatibility tuple: device model, exact iOS build, region, carrier/plan, SIM/eSIM mode, carrier bundle, network mode, Wi-Fi Calling/VoLTE, roaming and audio route.
- Native SIM merge, app-owned Twilio Conference, accessory capture and import-only workflow are separate pathway IDs. Do not merge their results.
- Use only authorized test SIMs and consenting participants; speak synthetic phrases only.
- Keep raw recordings and personal data in an approved private evidence store. Public rows contain sanitized metadata and checksums only.
- Mark untested cells `NOT RUN`, not Pass. Mark simulator-only checks `SIMULATOR`, never Physical.
- Feasibility requires at least 3 successful core runs on the exact tuple. A production support claim requires at least 20 consecutive successful core runs plus interruption and route-change scenarios.

## Compatibility tuple register

| Tuple ID | Pathway | iPhone model | iOS version + build | Country/region | Carrier + plan | SIM/eSIM | Carrier bundle | VoLTE | Wi-Fi Calling | Roaming | Route | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T-001 | NOT RUN | — | — | — | — | — | — | — | — | — | — | NOT RUN |

## Per-tuple run matrix

Create one row per attempt. Keep all failures and inconclusive runs; never overwrite them with a later pass.

| Tuple ID | Run ID | Scenario | Repeat index / required | Local speech | Remote speech | Channels | Per-channel activity | Gaps / clipping / latency | Consent evidence ref | Artifact SHA-256 | Outcome | Reviewer |
|---|---|---|---|---|---|---:|---|---|---|---|---|---|
| T-001 | — | S01 outgoing | 1/3 | NOT RUN | NOT RUN | — | — | — | — | — | NOT RUN | — |
| T-001 | — | S02 incoming | 1/3 | NOT RUN | NOT RUN | — | — | — | — | — | NOT RUN | — |
| T-001 | — | S03 merge | 1/3 | NOT RUN | NOT RUN | — | — | — | — | — | NOT RUN | — |
| T-001 | — | S04 merge rejected | 1/1 | — | — | — | — | — | — | — | NOT RUN | — |
| T-001 | — | S05 hold/resume | 1/1 | NOT RUN | NOT RUN | — | — | — | — | — | NOT RUN | — |
| T-001 | — | S06 call waiting | 1/1 | NOT RUN | NOT RUN | — | — | — | — | — | NOT RUN | — |
| T-001 | — | S07 route change | 1/1 | NOT RUN | NOT RUN | — | — | — | — | — | NOT RUN | — |
| T-001 | — | S08 network transition | 1/1 | NOT RUN | NOT RUN | — | — | — | — | — | NOT RUN | — |
| T-001 | — | S09 background/suspension | 1/1 | NOT RUN | NOT RUN | — | — | — | — | — | NOT RUN | — |
| T-001 | — | S10 termination/interruption | 1/1 | — | — | — | — | — | — | — | NOT RUN | — |
| T-001 | — | S11 dual SIM | 1/1 | NOT RUN | NOT RUN | — | — | — | — | — | NOT RUN | — |
| T-001 | — | S12 roaming | 1/1 | NOT RUN | NOT RUN | — | — | — | — | — | NOT RUN | — |

## Pathway-specific evidence

For native SIM merge, determine whether the carrier presents one mixed participant or two independently attributable audio legs. Twilio dual-channel conference recording does not mean per-speaker separation. A two-channel WAV is insufficient unless both channels are inspected and both endpoints' synthetic phrases are independently intelligible.

For app-owned Twilio Conference, record that both participants were called as separate provider legs. This result cannot be used as native SIM-call evidence.

For import-only tests, verify file validation, catalog persistence, playback, export and deletion. This proves archive reliability only.

## Sign-off

| Gate | Required evidence | Status |
|---|---|---|
| Exact tuple recorded | All tuple fields complete | NOT RUN |
| Consent and notice | Evidence for every participant | NOT RUN |
| Three feasibility repeats | 3/3 core calls with both sides intelligible | NOT RUN |
| Audio inspection | Channel count/activity, duration, clipping, gaps and truncation | NOT RUN |
| Failure handling | Merge rejection/no-answer/interruption fail closed | NOT RUN |
| Production support threshold | 20 consecutive core passes + route/interruption tests | NOT RUN |
| Independent review | Reviewer checks sanitized evidence and secure artifact | NOT RUN |

No tuple is certified until all applicable gates are reviewed. A passing tuple does not generalize to another carrier, plan, iOS build, region or route.
