# iOS SIM Call Recording: Technical Research Matrix

> Status: research baseline, not a claim of universal feasibility.  
> Last reviewed: 2026-11-19  
> Scope: recording both sides of ordinary carrier/PSTN calls on iPhone, with explicit consent and lawful use.

## 1. Objective and evidence standard

The project investigates every technically plausible capture path rather than assuming a single implementation. Each path is evaluated independently for:

- Whether it captures both local and remote sides of a real cellular call.
- Supported iPhone models, exact iOS builds, carriers, regions, SIM configurations and audio routes.
- Consent, disclosure and local-law requirements.
- Repeatability, audio quality, interruption recovery and operational cost.
- App Store eligibility versus accessory-, carrier- or research-only distribution.

A pathway is not supported based on API availability, marketing claims, simulator behavior, or a successful one-off recording. It must pass the real-device acceptance criteria in section 6.

## 2. Platform constraints and confirmed facts

### 2.1 Native iOS recording

Apple added native Phone and FaceTime audio call recording in iOS 18. Availability is region-dependent. Apple's current support documentation lists multiple excluded regions, including the European Union, Iran and Oman. When native recording is available and enabled, participants receive an audible announcement and the recording is saved to Notes.

This is a user-facing system feature. No public third-party API has been identified that gives an arbitrary App Store application access to the Phone app's live cellular-call audio stream or native recording pipeline.

### 2.2 CallKit boundary

CallKit is intended for an application to integrate and manage its own VoIP calling experience with the system. It does not provide an interception API for calls carried by the native Phone application. Apple's Developer Technical Support responses explicitly distinguish an app-managed VoIP audio stream from a native cellular call stream.

### 2.3 Bluetooth is not an automatic capture entitlement

Bluetooth HFP is a bidirectional telephony audio route, but pairing an iPhone with an accessory does not itself grant a third-party iOS app access to both sides of a native call. An accessory-side recorder is a separate hardware research path and must be proven on the actual accessory/audio topology.

### 2.4 Review and privacy

Apple's App Review Guidelines require explicit consent and a clear indication when recording or logging user activity. Privacy disclosures must explain collection, use, retention, deletion and consent. Local recording laws may impose additional requirements; product UX must not assume one-party consent is universally sufficient.

## 3. Pathway matrix

| ID | Pathway | Capture location | iOS app-only | App Store outlook | Main dependency / blocker | Priority |
|---|---|---|---|---|---|---|
| P01 | Native Apple Phone recording | iOS Phone / Notes | No direct capture API established; investigate user-mediated workflow | Potential companion workflow, not a recorder replacement | OS version, region, user action, export/import surface | High |
| P02 | Three-way conference bridge | Carrier conference + remote bridge | Yes, as call orchestration; audio captured server-side | Conditional | Carrier supports conference/merge; bridge number and backend | Highest |
| P03 | Carrier recording service/API | Carrier network | Conditional | Conditional | Carrier contract, API, regional availability | High |
| P04 | Conditional call forwarding / network routing | Carrier network | No universal path | Conditional | Carrier-specific forwarding; inbound-only limitations; caller disclosure | Medium |
| P05 | App-owned VoIP/PSTN hybrid | App/backend | Yes, for calls actually owned by app | Plausible with compliant VoIP design | User must place/receive calls through app; PSTN gateway | High |
| P06 | Bluetooth HFP accessory-side recorder | Dedicated accessory | No; accessory firmware captures audio | Accessory-dependent | Hardware routing, HFP profile behavior, certification, proof of both directions | High |
| P07 | Wired / USB-C / Lightning external recorder | External hardware | No; external hardware captures audio | Accessory-dependent | Physical routing and device compatibility; adapter behavior | Medium |
| P08 | Speakerphone + external microphone | Acoustic environment | App can record microphone input only where OS permits; remote audio is acoustic | Conditional, limited quality | Speakerphone, ambient noise, mic permissions, route changes | Medium |
| P09 | Jailbreak-specific instrumentation | Modified iOS runtime | No | Research-only; not App Store viable | Jailbreak availability, model/build exploit chain, security and stability | Medium (isolated) |
| P10 | Private / undocumented frameworks or entitlements | iOS internals | Experimental only | Not production-reliable; rejection/breakage risk | Entitlements, ABI changes, OS updates, review | Medium (isolated) |
| P11 | CallKit / LiveCommunicationKit for app-owned calls | App-owned VoIP media pipeline | Yes | Plausible for app-owned calls | Does not solve native Phone app capture | High |
| P12 | Screen/audio recording and microphone APIs | iOS media capture APIs | No known general access to mixed cellular call audio | Not a native-call solution absent new public support | Protected/system audio routing and background restrictions | Low (verify, then close or reopen) |

### P01 — Native Apple recording companion

Investigate whether a companion app can guide users to the system recording feature and import recordings through supported user-mediated document/share workflows. Do not assume Notes has a public API that exposes every recording. Record regional feature availability and exact iOS version behavior.

### P02 — Conference bridge

Prototype the three-leg flow: establish the user-to-party call, dial a recording bridge, then merge. The bridge records each leg or mixed audio server-side and associates it with a consented session. Test incoming and outgoing orchestration, call waiting, merge failures, carrier restrictions, dual SIM and roaming. Commercial products describing this model are evidence that the workflow exists in some markets, not proof of universal carrier support.

### P03 — Carrier integration

Create a carrier capability register. For each operator, capture supported countries, plans, business/consumer eligibility, API/contract requirements, inbound/outbound coverage, recording notification behavior, retention and data residency. Do not mark a carrier supported based only on call forwarding availability.

### P04 — Forwarding

Test conditional forwarding codes and carrier account controls only with authorized test SIMs. Distinguish unconditional, busy, no-answer and unreachable forwarding. Document whether the forwarding path can preserve original caller identity and whether it can record both directions. Outbound calls require a separate design.

### P05 / P11 — App-owned VoIP

Build a separate product mode in which calls are originated or terminated by the app and media is controlled by the app/backend. Use CallKit for system integration where appropriate. This is a legitimate alternative calling mode, not transparent recording of calls placed in Apple's Phone app.

### P06 — Bluetooth hardware spike

Design a controlled prototype with a known Bluetooth chipset and HFP implementation. Verify uplink and downlink separately, including codec, sample rate, channel mapping, call setup, route switching and reconnect. The iPhone app should manage the accessory and retrieve recordings; do not rely on the app receiving raw cellular-call PCM. Document accessory program and radio certification implications before productization.

### P07 — Wired external hardware

Evaluate audio interface/dongle topologies independently: analog headset pass-through, USB audio accessory and device-specific adapters. Determine whether the accessory receives both directions electrically and whether the iPhone recognizes it as a telephony route. A microphone-only input is not two-sided call capture.

### P08 — Acoustic fallback

Treat speakerphone recording as a low-quality fallback, not a guaranteed solution. Measure intelligibility, echo, clipping, environmental noise, microphone permission behavior and background interruptions. Clearly indicate recording to participants.

### P09 / P10 — Isolated research

Keep jailbreak and private-API experiments in a separate research target/repository or isolated branch. Record exact device identifier, iOS build, exploit/entitlement prerequisites, reproducibility, crash rate and security implications. Never make production support or App Store claims from these results.

## 4. Compatibility test dimensions

Every test record must include all fields below. "iPhone model" alone is not a compatibility statement.

| Dimension | Required values |
|---|---|
| Hardware | Marketing model, hardware identifier, generation, chipset where relevant |
| OS | iOS version, exact build, security response / beta status |
| Region | Device region, physical location, language, Apple feature availability |
| Carrier | Operator, country, plan class, carrier bundle version where available |
| SIM | Physical SIM/eSIM, slot/line, dual-SIM configuration, roaming |
| Network | LTE/5G, Wi-Fi Calling state, VoLTE/IMS state where observable |
| Call scenario | Incoming/outgoing, answered/rejected, call waiting, hold, conference, emergency-call exclusion |
| Route | Receiver, speaker, wired headset, Bluetooth HFP, external accessory |
| Pathway | P01-P12, app/backend/firmware versions, configuration |
| Consent | Initiator, disclosure method, audible/visual indication, participant confirmation |
| Audio | Local/remote intelligibility, duration, clipping, gaps, latency, channel separation |
| Reliability | Setup success, merge success, interruption recovery, app termination, network transition |
| Distribution | App Store, carrier agreement, accessory-dependent, sideload/research-only |
| Evidence | Test operator, timestamp, raw logs, anonymized sample, repeat count, issue links |

Use a compatibility tuple:
(device, iOS build, region, carrier/plan, SIM, network, call scenario, route, pathway, app/firmware version).

A pass on one tuple does not imply support for neighboring tuples.

## 5. Research and implementation architecture

Keep pathway-specific capture mechanisms behind adapters. The product must not couple UI to any one recording method.

- **App shell:** SwiftUI navigation, onboarding, consent, session history and settings.
- **Recording orchestration:** pathway selection, capability checks, session lifecycle and state machine.
- **Pathway adapters:** Native companion, Conference Bridge, Carrier, App-owned VoIP, Accessory, Acoustic and Experimental.
- **Backend:** bridge orchestration, carrier integrations, encrypted media ingress, session metadata and retention controls.
- **Storage:** encryption at rest, access control, deletion, export and retention enforcement.
- **Diagnostics:** structured redacted logs, pathway health, failure taxonomy and opt-in test telemetry.
- **Test lab:** device/carrier/region matrix, repeatable call scripts, audio fixtures and evidence archive.

Suggested lifecycle states: idle, preparing, awaiting_consent, connecting, recording, finalizing, completed, failed, cancelled, interrupted and degraded. Never label a session "recorded" until both required audio directions have been verified or the limitation is clearly disclosed.

## 6. Acceptance gates for a supported pathway

A pathway is not production-supported until it passes all applicable gates:

1. Reproducible capture of both local and remote speech on physical devices.
2. At least 20 consecutive successful sessions per declared compatibility tuple, with failures recorded rather than discarded.
3. Explicit consent and clear recording indication for all participants, plus jurisdiction-specific legal review.
4. Correct behavior for call waiting, hold, merge failure, route changes, app suspension/termination, network transitions and interrupted uploads.
5. Measured audio quality, completeness, clipping, dropouts and synchronization against defined thresholds.
6. Encryption in transit and at rest, least-privilege access, retention/deletion/export controls and auditable access.
7. Documented exact compatibility tuple and reproducible test evidence.
8. Explicit distribution classification: App Store, carrier-dependent, accessory-dependent, or research-only.

## 7. Initial execution plan

### Track A — Conference bridge proof (highest near-term value)
- Specify inbound/outbound call state machines.
- Identify test carriers and conference-call capability.
- Implement a minimal bridge backend with consent event, recording, session metadata and deletion.
- Validate real merge behavior on physical iPhones and multiple carriers.

### Track B — Bluetooth accessory feasibility
- Select one HFP-capable development platform.
- Produce a signal-path diagram and prototype.
- Verify remote and local directions independently.
- Decide whether custom hardware can meet quality, certification and cost requirements.

### Track C — Native iOS and API boundary
- Maintain an OS/region feature matrix.
- Re-check public APIs and Apple documentation each major iOS release.
- Prototype user-mediated import of native recordings without private API assumptions.

### Track D — Carrier and forwarding research
- Build an operator capability questionnaire and evidence register.
- Separate network recording, forwarding, conference and outbound coverage.

### Track E — Isolated experimental research
- Maintain separate build configurations and explicit non-production labels.
- No private API or jailbreak dependency may leak into the App Store target.

## 8. Evidence register and references

Primary sources:

1. Apple Support — Record and transcribe a call on iPhone: https://support.apple.com/guide/iphone/iph57c6590e9/27/ios/27
2. Apple Developer — CallKit: https://developer.apple.com/documentation/callkit
3. Apple App Review Guidelines (recording consent, privacy and user data): https://developer.apple.com/app-store/review/guidelines/
4. Apple Developer Forums — DTS discussion of native cellular call audio access: https://developer.apple.com/forums/thread/841340
5. Apple Developer Forums — DTS discussion of native Phone call interception: https://developer.apple.com/forums/thread/835552
6. Apple Developer Forums — Bluetooth/HFP and background recording discussion: https://developer.apple.com/forums/thread/816408
7. Apple Bluetooth Accessory Design Guidelines: https://developer.apple.com/accessories/Accessory-Design-Guidelines.pdf

Secondary product evidence (not platform guarantees):

- REKK App Store listing describes a three-way conference calling workflow: https://apps.apple.com/us/app/rekk-call-recorder/id1475739728

## 9. Open questions

- Can any supported public API expose a user-mediated native recording file reliably across relevant regions and OS releases?
- Which target carriers permit three-way conference merge for consumer and business plans?
- Can a selected HFP accessory capture both directions at the hardware level on current iPhones without relying on iOS app audio access?
- Which USB audio accessory topologies preserve telephony routing and both audio directions?
- What are the exact App Store review expectations for each workflow and hardware configuration?
- Which legal regimes require all-party consent, audible notification, retention limits or data localization?

## 10. Change control

Update this document when new primary evidence or reproducible test results appear. Each claim should be tagged as one of:
- **Confirmed:** primary documentation or reproducible physical-device test.
- **Observed:** a test result limited to a stated configuration.
- **Hypothesis:** plausible but not yet demonstrated.
- **Rejected:** failed experiment or authoritative platform limitation, with evidence and scope.

Do not silently convert a hypothesis into a product capability.
