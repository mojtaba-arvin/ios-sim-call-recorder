# iOS SIM-call recording and conference-provider evaluation

**Research snapshot:** 2026-11-19  
**Status:** evidence baseline; not a provider certification or carrier-compatibility claim.

## Executive decisions

1. Keep native cellular-call capture and provider conference bridging as separate recording pathways.
2. Do not use CallKit as evidence of access to native Phone-call audio. Apple's CallKit documentation describes the system calling UI and coordination for an app's VoIP services.
3. Region availability is a hard capability input. Apple's current iPhone call-recording guide lists the European Union, Iran and Oman among regions where its built-in recording feature is unavailable.
4. Keep Twilio as the first adapter target only for the current stack; do not infer it is the best product provider. Telnyx is now a strong second candidate and must be compared before live integration is locked.
5. Preserve Vonage as a viable alternative. Telnyx is now a strong second candidate: its conference APIs, dual-channel recording, region selection and signed webhooks are documented. Compare both providers before locking product selection.
6. Never retry an ambiguous provider create/join operation without reconciliation. A transactional outbox gives at-least-once delivery, not exactly-once remote effects.

## iOS platform boundary

- [Apple CallKit](https://developer.apple.com/documentation/callkit) provides the system calling interface and coordinates an app's VoIP services. It is not a public native Phone-call recording API.
- [UIKit URL opening](https://developer.apple.com/documentation/uikit/uiscene/open%28_%3Aoptions%3Acompletionhandler%3A%29) supports the `tel` scheme by handing the URL to the system app. It does not expose an API to merge calls or read Phone-call audio.
- [Default calling app guidance](https://developer.apple.com/documentation/CallKit/Preparing-your-app-to-be-the-default-calling-app) describes the iOS 18.2+ default-calling-app entitlement and VoIP fallback behavior; it is not a permission to intercept the native Phone app.
- [Apple iPhone call recording guide](https://support.apple.com/guide/iphone/record-and-transcribe-a-call-iph57c6590e9/27/ios/27) documents built-in recording in select regions and explicitly excludes the EU, Iran and Oman in the current guide.
- [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) section 2.5.14 requires explicit consent and a clear visual and/or audible indication when recording user activity.

**Engineering consequence:** device model, iOS build, region, language, carrier, SIM setup, roaming, Wi-Fi Calling, VoLTE and call direction remain explicit compatibility dimensions. A feature appearing on one device or region does not establish universal support. Physical-device testing is mandatory.

## Provider comparison

| Capability | Twilio Programmable Voice | Vonage Voice API | Telnyx Voice API |
|---|---|---|---|
| Conference model | TwiML `<Dial><Conference>` or Participants API; Conference resource is not directly created | Named Conversation action in NCCO | Primary documentation review still incomplete for this exact workflow |
| Recording | Conference recording; account-level dual-channel behavior | Conversation recording; split stereo caller-vs-received tracks documented | Do not claim parity until primary docs are verified |
| Channel semantics | Channel 1 = first participant with recording enabled; channel 2 = all other conference audio | Split recording is described as one channel sent by caller and one channel heard by caller | Unverified |
| Callback security | `X-Twilio-Signature`; validate exact public URL and request parameters/body | Signed JWT webhooks documented | Ed25519 webhook signatures documented in primary API guides |
| Retry/replay | Webhook retries require event deduplication; do not assume participant-create POST is idempotent | Event webhook retries documented for selected failure responses; deduplicate | Duplicate/out-of-order webhooks; command_id duplicate suppression documented for 60 seconds only |
| Selection status | First adapter already present in stack; reconciliation strategy required | Alternative for later controlled comparison | Strong second candidate; cost/region/carrier comparison pending |

### Twilio-specific findings

- [Conference resource](https://www.twilio.com/docs/voice/api/conference-resource): conferences are created through TwiML or the Participants API, not by directly POSTing a Conference resource.
- [Participants API](https://www.twilio.com/docs/voice/api/conference-participant-resource): a participant can be added to an active Conference or a named Conference. Outbound participant creation requires `from` and `to`; a phone-number `from` must be a Twilio number or a verified outgoing caller ID. The docs warn against PII in `FriendlyName`. Use a deterministic opaque value only. Active Participant resources are not a historical participant log.
- [Conference callbacks](https://www.twilio.com/docs/voice/twiml/conference): callback configuration from the first participant is authoritative; subsequent participant callback URLs are ignored. Configure it on the first join and persist participant lifecycle events.
- [Duplicate participant label error 16025](https://www.twilio.com/docs/api/errors/16025): participant labels must be unique within a conference.
- [Conference recording settings](https://www.twilio.com/docs/voice/recording-settings): dual-channel is not per-participant isolation. Download with `RequestedChannels=2` when the recording supports it.
- [Dual-channel GA changelog](https://www.twilio.com/en-us/changelog/dual-channel-conference-recordings-as-default-is-now-ga): public-key encryption and external storage account settings are listed as limitations for default dual-channel conference output.

The reviewed documentation does **not** establish a general idempotency guarantee for Conference Participant creation. The adapter must use a stable opaque correlation key (for example a deterministic per-session conference name plus unique participant labels), inspect provider state after uncertain outcomes, and only retry when reconciliation establishes that the effect did not happen. Provider API behavior and account configuration must be verified before production use.

### Telnyx-specific findings

The primary Telnyx documentation now confirms a substantially more complete conference path than the initial research suggested:

- [Commands and resources](https://developers.telnyx.com/docs/voice/programmable-voice/voice-api-commands-and-resources) exposes conference create/list/retrieve, participant join/leave, and conference recording start/stop.
- [Conference recording start](https://developers.telnyx.com/api-reference/conference-commands/conference-recording-start) supports WAV/MP3, `channels=dual`, `play_beep`, and a selectable recording region including Europe and Middle East. Dual output places the conference creator on channel 1 and all other participants together on channel 2; it is not per-participant isolation.
- [Bridge calls](https://developers.telnyx.com/api-reference/call-commands/bridge-calls) supports bridging two Call Control legs and exposes recording controls including `record_channels` and `record_track`.
- [Webhook delivery](https://developers.telnyx.com/docs/voice/programmable-voice/receiving-webhooks) is not ordered and may be duplicated; validate the Ed25519 signature and deduplicate by webhook event ID.
- Telnyx documents `command_id` deduplication for duplicate commands for the same call/conference, but the documented duplicate-command suppression window is **60 seconds**. It is not a durable exactly-once guarantee for long-delayed outbox retries.
- [Recording storage](https://developers.telnyx.com/docs/voice/programmable-voice/storing-call-recordings) sends a recording-ready webhook; the documented Telnyx-hosted recording URL is time-limited (10 minutes in the example). Treat it as a secret and never place it in logs or durable outbox payloads.

This makes Telnyx a strong alternative to Twilio for the next controlled comparison, especially where Europe/Middle East recording locality matters. The docs do not establish a universal carrier-merge capability, per-person separation, or market-by-market number availability. A beep is an audible notice, not proof of affirmative consent.

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

- Verify current Twilio Participant API behavior for deterministic opaque conference names, participant labels, concurrent creation and post-timeout reconciliation using a test account before enabling a live adapter. `FriendlyName` is not globally unique over time; only one conference with a given name can be in progress at once.
- Complete Telnyx market-specific number availability, pricing, recording retention/data residency and test-account validation; verify the exact 60-second command_id behavior against long outbox retries.
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
- Twilio Conference TwiML callbacks: https://www.twilio.com/docs/voice/twiml/conference
- Telnyx commands/resources: https://developers.telnyx.com/docs/voice/programmable-voice/voice-api-commands-and-resources
- Telnyx conference recording start: https://developers.telnyx.com/api-reference/conference-commands/conference-recording-start
- Telnyx bridge calls: https://developers.telnyx.com/api-reference/call-commands/bridge-calls
- Telnyx webhook delivery: https://developers.telnyx.com/docs/voice/programmable-voice/receiving-webhooks
- Telnyx recording storage: https://developers.telnyx.com/docs/voice/programmable-voice/storing-call-recordings
- UIKit open URL: https://developer.apple.com/documentation/uikit/uiscene/open%28_%3Aoptions%3Acompletionhandler%3A%29
- Vonage recording: https://developer.vonage.com/en/voice/voice-api/concepts/recording
- Vonage webhook reference: https://developer.vonage.com/en/voice/voice-api/webhook-reference
- Vonage NCCO: https://developer.vonage.com/en/voice/voice-api/ncco-reference
