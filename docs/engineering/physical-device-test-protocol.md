# Physical-device feasibility test protocol

- Status: draft protocol
- Owner: project engineering
- Related: [recording pathway matrix](../research/recording-pathways.md)

## 1. Purpose

Determine whether a pathway captures both directions of a real carrier call on a precisely identified configuration. This protocol is not a substitute for legal review, carrier authorization or participant consent.

## 2. Preconditions

- Use test SIMs and accounts authorized for the experiment.
- Obtain explicit consent from every participant before recording.
- Use synthetic spoken test phrases; do not use personal, financial or confidential call content.
- Record the device hardware identifier and exact iOS build.
- Record carrier, plan class, SIM/eSIM, network mode, region and audio route.
- Synchronize test clocks and assign a unique test-run ID.
- Confirm storage encryption and access restrictions before retaining any audio fixture.

## 3. Test phrase set

Use a fixed phrase set spoken separately by each endpoint:
- Local endpoint: "LOCAL TEST", followed by digits zero through nine at a steady pace.
- Remote endpoint: "REMOTE TEST", followed by digits nine through zero at a steady pace.
- Both endpoints: simultaneous speech for five seconds to assess overlap and channel separation.
- Silence: five seconds at call start and end to detect truncation and false-positive recording.

Do not reuse the phrase set as a substitute for subjective intelligibility review.

## 4. Per-run procedure

1. Verify and log the complete compatibility tuple.
2. Start the pathway using the documented user flow.
3. Complete consent and disclosure steps; capture evidence of the indication without recording personal information.
4. Establish the cellular call and verify both endpoints can hear each other.
5. Speak the phrase set in the defined order.
6. Exercise the scenario under test (for example incoming/outgoing, hold, call waiting, route switch or conference merge).
7. End the call normally and wait for finalization/upload to complete.
8. Verify the artifact exists, duration is plausible, playback works and both directions are intelligible.
9. Record failures, gaps, clipping, distortion, latency and any state-machine mismatch.
10. Delete the test recording according to the test retention policy after evidence review.

## 5. Required scenarios

| Scenario ID | Scenario | Required observation |
|---|---|---|
| S01 | Outgoing one-to-one call | Both directions captured from answer to hang-up |
| S02 | Incoming one-to-one call | Both directions captured; incoming call UI does not break session |
| S03 | Conference/merge | Merge succeeds and each expected participant is audible |
| S04 | Merge rejected or unsupported | Safe failure; no false "recording" success state |
| S05 | Hold and resume | Correct pause/resume semantics and no silent truncation |
| S06 | Call waiting | Existing session behavior is explicit and recoverable |
| S07 | Audio route change | Receiver/speaker/Bluetooth/wired transitions are recorded |
| S08 | Network transition | Cellular/Wi-Fi Calling transition does not corrupt session silently |
| S09 | App background/suspension | Lifecycle behavior matches documented platform capability |
| S10 | App termination / interruption | Recoverable state or explicit failed/incomplete status |
| S11 | Dual SIM | Correct line is selected and recorded in evidence |
| S12 | Roaming | Carrier-dependent behavior is measured, not assumed |

Not every scenario applies to every pathway. Mark non-applicable with a reason; do not silently omit it.

## 6. Evidence record template

Create one record per run. Never put phone numbers, names, raw audio or other personal data in public issues.

| Field | Value |
|---|---|
| Test run ID | |
| Date/time (UTC) | |
| Pathway ID and version | |
| iPhone marketing model | |
| Hardware identifier | |
| iOS version and exact build | |
| Device region / test country | |
| Carrier / country / plan class | |
| Carrier bundle version | |
| SIM type / line / dual-SIM state | |
| Network / Wi-Fi Calling / roaming | |
| Call scenario ID | |
| Audio route | |
| App / backend / accessory firmware version | |
| Consent/disclosure evidence reference | |
| Local speech intelligible (yes/no/partial) | |
| Remote speech intelligible (yes/no/partial) | |
| Missing segments / gaps | |
| Clipping / distortion | |
| Measured latency / synchronization | |
| Setup / merge / finalization result | |
| Failure classification | |
| Artifact checksum / secure evidence reference | |
| Repeat index / total repeats | |
| Outcome (pass/fail/inconclusive) | |
| Reviewer and notes | |

## 7. Pathway-level decision

For feasibility confirmation, run the core scenario at least three times on the exact compatibility tuple and retain every failure and exclusion. Three successful repeats support a bounded feasibility result; they do not establish production support. A tuple may be called production-supported only after at least 20 consecutive successful core-scenario runs, with the required interruption and route-change scenarios also passing. Keep the two thresholds distinct in every report.

Possible outcomes:
- **Pass:** all required criteria met for this exact tuple.
- **Fail:** a required criterion was not met.
- **Inconclusive:** insufficient evidence, unstable test conditions or missing metadata.
- **Not applicable:** scenario does not apply, with a documented reason.

A result never generalizes automatically to another iPhone model, iOS build, carrier, region, plan or audio route.
