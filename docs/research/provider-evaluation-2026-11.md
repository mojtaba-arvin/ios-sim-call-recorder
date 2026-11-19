# iOS SIM-call recording and conference-provider evaluation

**Research snapshot:** 2026-11-19  
**Status:** evidence baseline; not a provider certification or carrier-compatibility claim.

## Executive decisions

1. Keep native cellular-call capture and provider conference bridging as separate recording pathways.
2. Do not use CallKit as evidence of access to native Phone-call audio. Apple's CallKit documentation describes the system calling UI and coordination for an app's VoIP services.
3. Region availability is a hard capability input. Apple's current iPhone call-recording guide lists the European Union, Iran and Oman among regions where its built-in recording feature is unavailable.
4. Keep Twilio as the first adapter target because the current backend stack already contains its signature verifier. Do not claim Twilio is the best universal provider.
5. Preserve Vonage as a viable alternative for a future controlled comparison. Telnyx remains research-only until primary documentation supports the exact call-control, recording-channel and idempotency requirements.
6. Never retry an ambiguous provider create/join operation without reconciliation. A transactional outbox gives at-least-once delivery, not exactly-once remote effects.

## iOS platform boundary

- [Apple CallKit](https://developer.apple.com/documentation/callkit) provides the system calling interface and coordinates an app's VoIP services. It is not a public native Phone-call recording API.
- [Apple iPhone call recording guide](https://support.apple.com/guide/iphone/record-and-transcribe-a-call-iph57c6590e9/27/ios/27) documents built-in recording in select regions and explicitly excludes the EU, Iran and Oman in the current guide.
- [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) section 2.5.14 requires explicit consent and a clear visual and/or audible indication when recording user activity.

**Engineering consequence:** device model, iOS build, region, language, carrier, SIM setup, roaming, Wi-Fi Calling, VoLTE and call direction remain explicit compatibility dimensions. A feature appearing on one device or region does not establish universal support. Physical-device testing is mandatory.

## Provider comparison

| Capability | Twilio Programmable Voice | Vonage Voice API | Telnyx Voice API |
|---|---|---|---|
| Conference model | TwiML `<Dial><Conference>` or Participants API; Conference resource is not directly created | Named Conversation action in NCCO | Primary documentation review still incomplete for this exact workflow |
| Recording | Conference recording; account-level dual-channel behavior | Conversation recording; split stereo caller-vs-received tracks documented | Do not claim parity until primary docs are verified |
| Channel semantics | Channel 1 = first participant with recording enabled; channel 2 = all other conference audio | Split recording is described as one channel sent by caller and one channel heard by caller | Unverified |
| Callback security | `X-Twilio-Signature`; validate exact public URL and request parameters/body | Signed JWT webhooks documented | Ed25519 webhook signature described in available API material; verify against primary docs before implementation |
| Retry/replay | Webhook retries require event deduplication; do not assume participant-create POST is idempotent | Event webhook retries documented for selected failure responses; deduplicate | Delivery can be duplicate/out-of-order; command IDs are documented with a limited deduplication window in currently available material |
| Selection status | First implementation target; reconciliation strategy required | Alternative for later physical comparison | Research only |

### Twilio-specific findings

- [Conference resource](https://www.twilio.com/docs/voice/api/conference-resource): conferences are created through TwiML or the Participants API, not by directly POSTing a Conference resource.
- [Participants API](https://www.twilio.com/docs/voice/api/conference-participant-resource): a participant can be added to an active Conference or a named Conference; active Participant resources are not a historical participant log.
- [Duplicate participant label error 16025](https://www.twilio.com/docs/api/errors/16025): participant labels must be unique within a conference.
- [Conference recording settings](https://www.twilio.com/docs/voice/recording-settings): dual-channel is not per-participant isolation. Download with `RequestedChannels=2` when the recording supports it.
- [Dual-channel GA changelog](https://www.twilio.com/en-us/changelog/dual-channel-conference-recordings-as-default-is-now-ga): public-key encryption and external storage account settings are listed as limitations for default dual-channel conference output.

The reviewed documentation does **not** establish a general idempotency guarantee for Conference Participant creation. The adapter must use a stable opaque correlation key (for example a deterministic per-session conference name plus unique participant labels), inspect provider state after uncertain outcomes, and only retry when reconciliation establishes that the effect did not happen. Provider API behavior and account configuration must be verified before production use.

### Vonage-specific findings

- [Recording guide](https://developer.vonage.com/en/voice/voice-api/concepts/recording): named Conversations can be recorded; split recording is described as stereo caller-vs-received audio.
- [Webhook reference](https://developer.vonage.com/en/voice/voice-api/webhook-reference): signed webhooks, event types and fallback/retry behavior are documented.
- [NCCO reference](https://developer.vonage.com/en/voice/voice-api/ncco-reference): Conversation lifecycle and recording options are configured through call-control instructions.

This makes Vonage a plausible second adapter candidate, but does not establish cellular conference-merge compatibility for any target carrier.

## Architecture consequences

- Outbox rows contain only opaque session/participant references. Phone numbers, tokens, signatures, recording URLs and audio are prohibited.
- Persist provider/account/session -> Conference SID mappings and provider/account/session/participant-ref -> Call SID mappings. Treat mappings as immutable; conflicting ownership must fail closed.
- Persist participant lifecycle callbacks because live provider Participant resources may disappear after a conference ends.
- The dispatcher must lease in a short database transaction, perform provider I/O outside the transaction, reconcile first, persist discovered resource identifiers, then acknowledge using the current lease token.
- If provider state is unknown, defer and reconcile again; do not issue a potentially duplicating side effect.
- Validate recording channel semantics during account preflight and again in physical acceptance tests.
- CI must use deterministic mocks only. No credentials, paid API calls or real phone calls in CI.

## Evidence gaps / next research

- Verify current Twilio Participant API behavior for deterministic conference names, participant labels, concurrent creation and post-timeout reconciliation using a test account before enabling a live adapter.
- Complete primary-source Telnyx research for conference lifecycle, recording channels, webhook signature verification, retries and command idempotency.
- Compare Vonage and Twilio with the same physical-device/carrier scenarios and the same consent/audio-verification acceptance protocol.
- Test SIM-call merge behavior on each target carrier/device/region combination. Provider conference docs cannot prove carrier support.
- Define lawful recording, consent, data residency, retention and deletion requirements for each launch market.

## References

- Apple CallKit: https://developer.apple.com/documentation/callkit
- Apple iPhone call recording availability: https://support.apple.com/guide/iphone/record-and-transcribe-a-call-iph57c6590e9/27/ios/27
- Apple App Store Review Guidelines: https://developer.apple.com/app-store/review/guidelines/
- Twilio Conference: https://www.twilio.com/docs/voice/api/conference-resource
- Twilio Participants: https://www.twilio.com/docs/voice/api/conference-participant-resource
- Twilio Recording settings: https://www.twilio.com/docs/voice/recording-settings
- Vonage recording: https://developer.vonage.com/en/voice/voice-api/concepts/recording
- Vonage webhook reference: https://developer.vonage.com/en/voice/voice-api/webhook-reference
- Vonage NCCO: https://developer.vonage.com/en/voice/voice-api/ncco-reference
