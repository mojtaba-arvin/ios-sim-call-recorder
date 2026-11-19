# iPhone call-audio capture pathway research

**Research snapshot:** 2026-11-19  
**Scope:** native cellular calls across iPhone generations, iOS releases, regions, SIM/network configurations and external accessories.  
**Status:** public-source assessment; no physical-device or carrier certification is implied.

## Executive conclusion

There is no supported public iOS API that lets an ordinary third-party app tap the live audio stream of the native Phone app. Apple DTS explicitly states that an app cannot access the audio of a call it does not carry. CallKit coordinates an app's own VoIP audio; it does not grant access to Phone.app audio.

Therefore the product must expose multiple distinct pathways and report their evidence/limitations instead of claiming one universal recorder.

## Pathway comparison

| Pathway | Captures native SIM call? | iPhone / OS dependency | Audio quality and both sides | Automation | Product status |
|---|---|---|---|---|---|
| Apple Phone call recording | Yes, built into Phone.app in supported markets | iOS 18.1+ and Apple's supported region/language; one-to-one call | System-generated recording; both parties hear recording announcement | User starts/stops in Phone; user exports audio from Notes | First-class user-mediated pathway |
| Separate external recorder + speakerphone | Can acoustically capture the audible conversation | Broad device coverage if speakerphone works; separate recorder required | Both sides only if remote speaker and local voice are clearly audible; room noise/echo vary | Manual | Practical fallback, not app-internal capture |
| Purpose-built wired call-recording accessory | Potentially, only if accessory actually receives both call directions | Exact iPhone connector, accessory protocol, iOS compatibility and routing must be verified | Depends on accessory's electrical/acoustic topology; never infer stereo separation | Usually accessory-specific | Experimental hardware validation |
| Bluetooth call-recording accessory | Potentially as a standalone accessory, not through a normal app tap | Exact accessory and Bluetooth call route | HFP route and firmware-specific; verify both sides in the produced file | Accessory-specific | Experimental hardware validation |
| Carrier conference bridge | Potentially, if carrier permits merging the SIM call with a provider leg | Carrier, tariff, country, VoLTE/Wi-Fi Calling, SIM setup and device | Provider may receive one mixed carrier leg; dual-channel does not guarantee speaker separation | Semi-manual or provider-driven | Existing backend track; physical test is blocking |
| App-owned VoIP call | Yes for calls carried by the app, not for a separate native SIM call | App network, codec and CallKit integration | Best control over both media legs, channel mapping and quality | High | Strong alternative product mode |
| ReplayKit / screen recording | No, not the private Phone.app call stream | ReplayKit app-audio/microphone scope | Captures app audio and microphone, not another app's native call stream | User initiated | Explicitly excluded for native SIM capture |
| Same-iPhone Voice Memos / microphone capture during Phone call | Not a dependable native call capture method | Audio-session ownership/interruption and route behavior | May be interrupted or fail to capture far-end audio | User initiated | Do not advertise without a reproducible device-specific proof |
| Private API / jailbreak / baseband interception | Not an acceptable supported route | Device compromise, OS-specific exploit/private interfaces | Fragile, insecure, non-App-Store-compatible | Variable | Rejected |

## Apple native Phone recording

Apple's current guide documents a user-operated Phone.app control:

1. Start a one-to-one cellular or FaceTime audio call.
2. The user taps More → Call Recording.
3. Both participants hear an audible recording notice.
4. The recording is saved in Notes, where the user can play, export or share the audio file.

Apple's iOS 18.1 release notes introduced call recording. The current guide lists the European Union, Iran and Oman among unavailable regions, alongside other markets. The feature must be evaluated against the current Apple availability guide at runtime/release time; the repository's market list is a conservative snapshot, not a substitute for Apple's live table.

The language availability table is also relevant. This implementation checks the published language prefixes conservatively, but the UI must still explain that actual feature visibility is controlled by iOS/region settings.

**Important integration boundary:** the app cannot silently start Phone.app recording, query its live call audio, or read the Notes recording database as if it were an app-owned file. The supported user journey is to export/share the audio file from Notes and then import it into the app. A future app shell should implement a document/file importer and validate the imported file; it should not attempt private Notes access.

Apple says its built-in feature is for calls with one other person. Do not assume it covers conference calls or carrier-merged group calls.

## External hardware routes

### Separate recorder with speakerphone

This is the broadest non-provider fallback: use iPhone speakerphone and a second independent recorder positioned to capture the speaker and the local participant. It is not elegant, but it does not require the iOS app to access Phone.app's audio session. It can work across a wide range of iPhone generations, subject to acoustic quality and local law.

Acceptance must test both voices independently, clipping, echo, room noise, distance, orientation, battery, and whether the iPhone switches routes during the call.

### Wired / USB-C / Lightning accessories

A USB-C or Lightning microphone/interface is not automatically a call recorder. It may only expose microphone input or app-owned audio. A viable accessory must prove that it receives both call directions through a documented, supported route, and that the resulting recording can be exported to the app. Validate exact iPhone model, connector, adapter, accessory firmware, call route and iOS version.

### Bluetooth accessories

Bluetooth HFP is a call audio route, not a public third-party API for tapping Phone.app's call stream. A purpose-built accessory may record internally, but the iOS app must not assume it can receive both directions from the Bluetooth route. Validate the accessory's own recording and import/export mechanism separately.

## Why ReplayKit and AVAudioSession are not a native-call solution

- ReplayKit documents recording screen video, audio from the app, and microphone audio. It does not grant access to a different app's private Phone call stream.
- AVAudioSession is the app's audio-session interface. Apple DTS explains that the app that owns a call's audio stream controls that stream; a third-party app cannot read another app's native call.
- Audio interruptions are normal system behavior. A recording app must observe interruption notifications and cannot assume microphone capture continues when Phone.app owns the call audio session.
- Apple's Accessibility "Add Audio in Calls" capability is for injecting app audio into a call after user enablement; it is not a receive/record API for the remote party.

## Device and carrier compatibility dimensions

Every physical run must record:

- Exact model identifier and marketed iPhone model/generation.
- iOS version and build.
- Device region setting, physical country and language.
- Carrier and carrier bundle version where available.
- Physical SIM / eSIM / dual-SIM configuration and active voice line.
- Roaming, LTE/5G, VoLTE and Wi-Fi Calling state.
- Incoming/outgoing direction and one-to-one vs conference call.
- Audio route: receiver, speaker, wired, Bluetooth HFP or accessory.
- Whether a recording announcement was played and affirmative consent was captured.
- Whether the exported audio contains local and remote speech, verified independently.

Do not infer model support from a marketing family name. For Apple-native recording, the first gate is the device's ability to run iOS 18.1 or later, followed by region/language and actual UI availability. For external accessories, the exact connector and accessory compatibility matrix matters more than the iPhone's CPU generation.

## Implementation started in this PR

- Added explicit pathway identifiers for Apple system recording, independent external recording and ReplayKit app capture.
- Added deterministic capability assessment for Apple's iOS 18.1 minimum, the currently documented unavailable markets and published language prefixes.
- The Apple-native route is returned as `requiresUserAction`, never as app-controlled automatic capture.
- Unknown region is returned as experimental; excluded region, old OS and ReplayKit-for-native-call are fail-closed.
- External recorder is reported as requiring separate hardware.
- Added unit tests for minimum OS, EU, Oman, supported-market user flow, unknown region, ReplayKit boundary and external hardware.

## Next steps

1. Add an app-shell document importer for recordings explicitly exported/shared by the user from Notes or an external recorder.
2. Validate audio containers, duration, sample rate, channel count and non-empty content; run local/remote speech verification where the test protocol provides known prompts.
3. Build a physical device/accessory matrix covering older Lightning iPhones, USB-C iPhones, iOS 18.1+, SIM/eSIM and Bluetooth/wired accessories.
4. Keep conference bridge and app-owned VoIP as independent capture strategies; do not conflate them with native Phone recording.
5. Only promote a pathway to supported after repeated two-way audio tests and legal/consent review.

## Primary references

- Apple iPhone call recording guide: https://support.apple.com/guide/iphone/record-and-transcribe-a-call-iph57c6590e9/27/ios
- Apple iOS 18.1 release notes: https://support.apple.com/en-us/121161
- Apple iOS feature availability: https://www.apple.com/ios/feature-availability/
- Apple DTS: no API to access a call not carried by the app: https://developer.apple.com/forums/thread/841340
- Apple DTS: native Phone call interception boundary: https://developer.apple.com/forums/thread/835552
- ReplayKit capture scope: https://developer.apple.com/documentation/ReplayKit
- AVAudioSession: https://developer.apple.com/documentation/AVFAudio/AVAudioSession
- Audio interruption handling: https://developer.apple.com/documentation/avfaudio/handling-audio-interruptions
- Apple Voice Memos with built-in/external microphones: https://support.apple.com/guide/iphone/make-a-recording-iph4d2a39a3b/27/ios
- Apple Add Audio in Calls (injection, not capture): https://developer.apple.com/documentation/avfaudio/adding-synthesized-speech-to-calls
