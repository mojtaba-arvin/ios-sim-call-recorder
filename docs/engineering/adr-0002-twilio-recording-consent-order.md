# ADR-0002: Collect consent before enabling Twilio conference recording

- Status: Accepted for the Twilio adapter design; provider implementation remains blocked.
- Date: 2026-11-19
- Related: issues #16, #18 and #2; [ADR-0001](adr-0001-pathway-adapters.md)

## Context

The current provider-neutral backend model accepts participant consent only after all participants have joined a bridge, then emits a `recording.start` outbox command. That is a useful abstract state-machine test, but it must not be mistaken for a valid Twilio conference implementation.

Twilio's current Voice API documentation describes conference creation through TwiML `<Conference>` or the Participants API. A conference is created when its first participant connects. The Participant create API exposes a `conferenceRecord` setting, including `record-from-start`, at participant-join time. The Recording API documents creation of a recording on an in-progress Call; for Conference recordings it documents pause/resume controls and explicitly says `stopped` is not supported. The reviewed public API does not document a general operation to start recording on an already-running conference after participants have joined.

References:
- [Twilio Voice Conference lifecycle](https://www.twilio.com/docs/voice/conference)
- [Twilio Conference Participant resource](https://www.twilio.com/docs/voice/api/conference-participant-resource)
- [Twilio Recording resource](https://www.twilio.com/docs/voice/api/recording)
- [TwiML Conference recording attributes](https://www.twilio.com/docs/voice/twiml/conference)

## Decision

1. **Consent precedes recording-enabled joins.** Every expected human participant must complete the consent/disclosure step before the first recording-enabled participant is added to the Twilio conference.
2. **Recording is configured at conference creation/join.** The first participant join that creates the conference must carry the provider-supported recording-from-start configuration. Later participants join an already-recording conference only after their own consent has been verified.
3. **No post-join consent shortcut.** A webhook that merely reports a participant joined is not consent evidence. A UI checkbox, caller assertion or generic conference beep is not proof of each participant's affirmative consent.
4. **No unsupported stop operation.** For a Twilio Conference recording, use pause/resume where the product needs to suspend recording while retaining the conference. Ending the conference ends the call and recording. Do not implement a fake `recording.stop` by calling an undocumented endpoint.
5. **Provider capabilities are explicit.** The provider port must declare recording start/stop/pause semantics. A provider that cannot satisfy the session's consent policy must reject the operation before any recording side effect.
6. **Carrier-merge path remains blocked.** A manually merged cellular call may arrive at Twilio as one mixed PSTN participant. The remote party is not necessarily a separately addressable provider participant and cannot be independently consent-verified by a DTMF prompt on that merged leg. Do not enable recording for this topology until a separate, auditable consent method is proven on physical devices.

## Consequences

- The current domain model and webhook reducer must be revised before a live Twilio command adapter is implemented: expected participant references and consent must be tracked before provider joins; the outbox must create/join a recording-enabled conference only after the preflight consent gate.
- The app-owned outbound-call flow can potentially collect consent by calling each participant into a preflight IVR, then joining them to a conference with recording enabled. This is a separate product mode and does not prove native SIM-call capture.
- The manual carrier-merge hypothesis needs physical-device/carrier validation and a consent design before backend implementation can claim it.
- Conference dual-channel output is not per-participant separation. Validate the actual downloaded media and each channel independently; a carrier-merged single participant may contain a mixed local/remote stream.

## Rejected alternatives

- Starting conference recording only after all participants are already joined: not supported by the reviewed Twilio API contract.
- Treating a beep or the initiating user's confirmation as consent from every participant: insufficient evidence.
- Treating a Conference `recording.stop` call as supported: the Recording API documents pause/resume for Conference recordings, not stop.
- Inferring separate speaker channels from a two-channel metadata field: conference channel semantics are not per-participant identity.

## Revisit when

Twilio publishes a supported API that starts a Conference recording after join, or physical-device tests establish a compliant, independently verifiable consent protocol for the carrier-merged topology. Re-check the official API docs before implementation because provider behavior can change.
