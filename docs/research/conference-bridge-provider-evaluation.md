# Conference Bridge Provider Evaluation

> Status: preliminary vendor capability research; no provider selected.
> Reviewed: 2026-11-19
> Related work: [P02 conference-bridge proof](../../issues/2)

## Product question

Can a user manually merge an ordinary carrier call with a recording bridge, allowing the bridge service to capture both directions without requiring an iOS app to intercept native Phone audio?

This is a carrier-dependent workflow. A provider's ability to create a conference does not prove that a user's carrier permits three-way calling, merge, hold/resume or the required caller-ID behavior.

## Provider comparison

| Provider | Conference control | Recording evidence | Channel behavior | Open validation |
|---|---|---|---|---|
| Twilio Programmable Voice | Conference and participant APIs; PSTN/SIP/Voice Client participants; hold, mute, remove and lifecycle callbacks | Conference recording supported; account-level dual-channel setting | Dual-channel conference file separates the first participant from all remaining participants mixed together; not one isolated channel per participant | Number availability, target-country reach, pricing, carrier merge compatibility, recording storage region, webhook and download behavior |
| Telnyx Voice API / TeXML | Conference creation and control documented | Cloud call recording supports single/dual channel; conference-specific channel semantics need proof | Do not assume dual-channel call recording semantics automatically apply to a conference | Confirm conference recording controls, two-way channel mapping, event lifecycle, supported countries and pricing |
| Vonage Voice API | Named conversations and conference workflows documented | Named conversation recording and split recording documented | Split recording separates initial caller speech from audio heard by that caller; validate mapping for the exact bridge topology | PSTN merge behavior, number availability, recording retention/region, pricing and exact webhook lifecycle |

## Findings and decisions

### Twilio — first candidate for a controlled proof

Twilio documents conferences with 2–250 participants, PSTN/SIP/Voice Client participation, participant management, conference lifecycle callbacks and conference recording. It also documents dual-channel conference recordings.

Important limitation: for a conference recording, channel one contains the first participant who joined with recording enabled, while channel two contains all other participants mixed together. This may be sufficient for a two-party bridge, but it is not per-participant isolation in a multi-party call. The dual-channel conference setting is account-level and must be explicitly enabled; media downloads must request two channels to preserve the dual-channel file.

**Decision:** use Twilio as the first provider candidate for a two-party physical-device proof, not as a committed production vendor.

### Telnyx — second candidate

Telnyx documents programmatic conference control through its Voice API and TeXML. Its cloud recording feature documents single- and dual-channel recordings. The research still needs to establish whether conference recordings support the required channel layout and whether the call recording controls map to a conference resource in the same way.

**Decision:** keep in the comparison until a conference-specific two-way recording test or explicit API documentation resolves channel semantics.

### Vonage — third candidate

Vonage documents recording a named conversation asynchronously and split recording, with the initial caller on one channel and the audio heard by that caller on the other. Recording events provide a media URL that requires application authentication to retrieve. Documentation currently describes a 30-day provider-side recording retention period; this must be reconciled with the product's own retention and deletion requirements.

**Decision:** retain as a viable technical candidate pending PSTN merge, region, retention, pricing and test evidence.

## Hard gates before vendor selection

1. Physical-device proof of inbound and outbound three-way merge on at least two target carrier/plan combinations.
2. Verified local and remote intelligibility; channel mapping measured using distinct synthetic phrases.
3. Explicit participant disclosure and affirmative consent before recording starts.
4. Signed webhook validation, replay protection, idempotent event processing and authenticated media retrieval.
5. Confirmed number availability, destination coverage, emergency-call exclusions and country-specific regulatory review.
6. Documented storage region, encryption, retention, deletion, export, subprocessors and incident handling.
7. Cost model for call minutes, conference participants, recording, storage, transfer and failed setup attempts.
8. Reproducible failure/recovery tests for hold, call waiting, merge failure, route changes and network transitions.

## Evidence labels

- **Confirmed:** directly documented by provider or reproduced in a physical-device test.
- **Observed:** reproduced only for the exact recorded test tuple.
- **Hypothesis:** technically plausible but not demonstrated.
- **Rejected:** failed or contradicted by authoritative evidence, with scope recorded.

## Sources

- [Twilio Voice Conference](https://www.twilio.com/docs/voice/conference)
- [Twilio Voice Recording Settings](https://www.twilio.com/docs/voice/recording-settings)
- [Twilio Conference Recording Resource](https://www.twilio.com/docs/voice/api/recording)
- [Telnyx Conference support](https://support.telnyx.com/en/articles/1130677-does-telnyx-support-conference-calls)
- [Telnyx Call Recording](https://support.telnyx.com/en/articles/5377454-call-recording)
- [Vonage Call Recording and Transcription](https://developer.vonage.com/en/voice/voice-api/concepts/recording)
- [Vonage Voice API Technical Details](https://developer.vonage.com/en/voice/voice-api/technical-details)
