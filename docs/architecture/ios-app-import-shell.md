# iOS app shell and user-mediated recording import

**Status:** first SwiftUI app target and document-picker import adapter implemented; simulator build and device validation remain CI/QA gates.

## Build

The Xcode project is generated from the root `project.yml` using XcodeGen. The application target is `CallRecorderApp`, deployment target iOS 16.0, and it links the reusable local `CallRecorderCore` Swift package.

```sh
brew install xcodegen
xcodegen generate
xcodebuild -project CallRecorder.xcodeproj -scheme CallRecorderApp -sdk iphonesimulator -configuration Debug CODE_SIGNING_ALLOWED=NO build
```

## Import flow

1. The user explicitly selects an audio file through SwiftUI's system document importer.
2. The adapter starts security-scoped access where required and always stops it after the copy/probe flow.
3. A lightweight container signature probe checks RIFF/WAVE, AIFF/AIFC, CAF, MP3 and ISO-BMFF/MP4-family headers. The filename extension is checked independently by the core validator.
4. The selected file is copied into an app-private staging directory under an opaque UUID filename.
5. AVAudioFile must successfully decode the staged file. Duration, sample rate and channel count are read from the decoded media, not guessed from its filename.
6. The core validator enforces the existing size, duration, sample-rate, channel-count and extension/container rules.
7. A validated file is moved into app-private recording storage under a new opaque UUID filename. A failed import removes its staged copy.

## Explicit limitations

- The current UI is an import shell, not a call recorder. It does not capture native Phone.app audio.
- It does not read Notes private storage or automate the Phone app. The user must export/share a recording and select it.
- It does not yet expose playback, deletion, retention settings, share/export, transcription, cloud upload or two-way speaker verification.
- Container signature checks and successful AVAudioFile decoding establish that a file is parseable audio; they do not prove that both call participants are audible.
- Hardware compatibility remains unverified until physical tests from Issue #20 are completed.
- Imported audio stays on-device. No network transfer is implemented.
