# External accessory compatibility assessment

**Status:** software assessment only. No accessory is certified by this matrix, and no physical iPhone result is implied.

## Why compatibility is tuple-specific

An accessory being paired, enumerated by iOS, or selected as an audio route does not prove that it receives both sides of a native cellular call. The app must not infer call recording capability from Bluetooth pairing, USB enumeration, a microphone permission, or an audio-route label.

The core assessment now requires all of the following before it will even return an accessory candidate:

- Exact iPhone model identifier and iOS version.
- Exact accessory model and firmware version.
- An active call route consistent with the accessory's declared signal path.
- A physical-device validation result before the tuple can be promoted beyond experimental.

## Route matching implemented in the core

| Accessory mechanism | Required active call route | Result when route matches | What remains unproven |
|---|---|---|---|
| Lightning / USB-C accessory | Wired or external accessory | Experimental candidate | Whether accessory receives uplink and downlink, connector/adapter compatibility, firmware behavior |
| Bluetooth call recorder | Bluetooth HFP | Experimental candidate | Whether accessory records both directions; pairing alone is insufficient |
| Contact/vibration recorder | Speaker | Experimental candidate | Whether handset vibration and speaker output yield intelligible local and remote speech |
| Separate acoustic recorder | Speaker | Experimental candidate | Placement, room acoustics, echo, noise and independent intelligibility |

A mismatched route is unavailable for that attempt. Missing model, firmware, iPhone model or iOS version fails closed as experimental; it is never silently upgraded to supported.

## Device generation and connector matrix

| iPhone family | Physical connector | Software rule |
|---|---|---|
| iPhone 14 and earlier | Lightning | Require a Lightning-specific accessory profile and the actually active wired/external route |
| iPhone 15 and later | USB-C | Require a USB-C-specific accessory profile and the actually active wired/external route |
| Bluetooth-capable iPhones | Bluetooth | Require active Bluetooth HFP route; Bluetooth LE pairing or generic connected state is not sufficient |
| Any iPhone with speakerphone | Acoustic/contact | Require speaker route; verify the exact case, attachment position, volume and room setup |

This is a connector planning matrix, not a claim that every accessory works on every model in the family. Adapters, cases, power requirements, iOS builds and accessory firmware remain independent compatibility dimensions.

## Promotion gate

A matching software route assessment remains **experimental**. To mark an exact tuple as observed/confirmed, capture three consented physical calls with the same device model, iOS build, accessory model/firmware, route, SIM, carrier, network and call direction. Both local and remote phrases must be independently intelligible at the beginning, middle and end. Record clipping, gaps, echo, noise, route changes and truncation. A separate WAV metrics report is supplementary and cannot identify speakers or prove intelligibility.

Never upload raw recordings, phone numbers, contacts, signatures or media URLs to GitHub. Publish only sanitized tuple metadata and evidence summaries.

## Executable evidence-promotion gate

The Swift core now models each physical attempt as a privacy-safe trial summary. It stores only an opaque attempt ID, timestamp, consent/notice confirmations, independent local/remote intelligibility results and artifact-integrity result—never audio, phone numbers, contacts or media URLs.

`AccessoryCompatibilityEvidence` is scoped to the exact device/OS/build/SIM/network/route context and accessory model/firmware. Its status remains insufficient unless at least three attempts have unique opaque IDs and every attempt confirms consent, recording notice, intelligible local speech, intelligible remote speech and artifact integrity. Any failed or incomplete attempt blocks promotion. This is a software gate over human-observed physical evidence; it cannot create or simulate that evidence.

## Route observation and carrier identity are separate proof requirements

A third-party app must not treat its own `AVAudioSession` route as proof of the active route used by Phone.app's private cellular-call session. The core now records the provenance of a route observation:

- `userReported`: useful only as a setup hint; never sufficient for physical evidence promotion.
- `appOwnedSessionObserved`: describes the app's own audio session (for example, app-owned VoIP); it does not prove the Phone.app route.
- `physicalTestObserved`: a route independently observed and recorded during the actual physical call test.
- `unknown`: no route evidence.

The three-call promotion gate requires `physicalTestObserved`. A user-selected "speaker" value or an app audio-route notification cannot promote a cellular accessory tuple.

Physical evidence also requires exact device region, physical test country, language, carrier identity, carrier bundle version, SIM configuration and network type. This prevents a result from one carrier bundle, SIM mode or network from being generalized to another. Do not put subscriber identifiers, phone numbers or raw call media in this tuple; carrier identity must be a non-personal carrier/bundle identifier.

## Per-direction quality gate

Each physical call now carries separate local and remote audio-quality summaries. Each direction must independently pass all of these checks:

- Speech intelligible at the beginning, middle and end of the call.
- Clipping within the accepted review threshold.
- No unacceptable audio gaps or dropouts.
- Echo within an acceptable range.
- Background noise within an acceptable range.

A positive local track cannot compensate for an unintelligible remote track, and a good average cannot hide a failure at the beginning, middle or end. The software model records reviewer outcomes only; it does not claim that these subjective checks are automated. The existing WAV analyzer can supply supplementary signal metrics, but waveform metrics alone cannot prove speaker identity or intelligibility.

Evidence-ledger hygiene is enforced as well: attempt IDs must be unique, non-numeric-only, 1–64 ASCII characters from letters, digits, hyphen and underscore. This reduces the risk of accidentally using a phone number or other personal identifier as a test ID. Trials must be listed in strictly increasing observation-time order. The validator does not accept free-form identifiers.
