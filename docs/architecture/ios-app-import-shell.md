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
2. The adapter starts security-scoped access where required and always stops it after the copy/probe flow. NSFileCoordinator coordinates the external document read.
3. The source size is checked against the core 500 MiB limit before copying, preventing oversized files from consuming app staging storage.
4. A lightweight container signature probe checks RIFF/WAVE, AIFF/AIFC, CAF, MP3 and ISO-BMFF/MP4-family headers. The filename extension is checked independently by the core validator.
5. The selected file is copied into an app-private staging directory under an opaque UUID filename.
6. AVAudioFile must successfully decode the staged file. Duration, sample rate and channel count are read from the decoded media, not guessed from its filename.
7. The core validator enforces the existing size, duration, sample-rate, channel-count and extension/container rules.
8. A validated file is moved into app-private recording storage under a new opaque UUID filename.
9. A small atomic JSON catalog stores only the opaque ID, container, byte count, duration and import timestamp. The original filename is not persisted. App-managed directories use complete file protection and are excluded from device backups.
10. The library lists catalog entries and lets the user delete an imported recording; missing media files are pruned from the catalog when the library loads. A failed import removes its staged copy.

## Explicit limitations

- The current UI is an import shell, not a call recorder. It does not capture native Phone.app audio.
- It does not read Notes private storage or automate the Phone app. The user must export/share a recording and select it.
- Playback, retention settings, share/export, transcription, cloud upload and two-way speaker verification are not implemented. Users can list and delete imported recordings.
- Container signature checks and successful AVAudioFile decoding establish that a file is parseable audio; they do not prove that both call participants are audible.
- Hardware compatibility remains unverified until physical tests from Issue #20 are completed.
- Imported audio stays on-device. No network transfer is implemented.
