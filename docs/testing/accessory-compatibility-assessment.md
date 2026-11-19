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
