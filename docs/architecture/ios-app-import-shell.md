# iOS app shell and user-mediated recording import

**Status:** SwiftUI app target, user-mediated import, local catalog, deletion, local playback, playback seeking/progress, audio interruption and output-route handling, system share/export, opt-in retention and catalog recovery implemented. Simulator CI is configured to build the app and execute the app-hosted XCTest suite; its result must be evaluated against the exact PR head commit. Physical-device and call-audio verification remain QA gates.

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

## Playback and export

- Playback is local-only through AVPlayer. The library supports play/pause, a seek slider, elapsed/total time, and resetting the playhead when the selected item reaches its end.
- A periodic AVPlayer time observer updates the playhead only while the user is not dragging the slider. The observer is removed before replacing or releasing its player.
- Audio interruptions pause playback. Playback does not resume automatically after an interruption; the user must explicitly press play.
- Disconnecting the current audio output (for example, unplugging headphones) pauses playback to avoid unexpectedly sending private audio to another output.
- The system share sheet exports the selected app-private audio file to a user-chosen destination or app. Export is user initiated; the app does not upload audio to a service.
- Playback and export URLs are resolved through the catalog and checked for file existence before use.
- Users should listen for both their own voice and the remote participant. Playback is a listening aid, not proof of two-way call capture; channel count alone is insufficient.

## Explicit limitations

- The current UI is an import shell, not a call recorder. It does not capture native Phone.app audio.
- It does not read Notes private storage or automate the Phone app. The user must export/share a recording from Notes or another source and select it.
- Container signature checks and successful AVAudioFile decoding establish that a file is parseable audio; they do not prove that both call participants are audible.
- Hardware compatibility remains unverified until physical tests from Issue #20 are completed.
- Imported audio stays on-device until the user explicitly chooses a destination in the system share sheet. No background network transfer is implemented.
- Transcription, cloud upload and automated two-way speaker verification remain future work.

## Retention, catalog recovery and storage maintenance

- Retention is opt-in. The default is **Never** (keep recordings until the user deletes them). The user can select 30, 90 or 365 days from the library's settings menu.
- The selected retention policy is stored locally using AppStorage. Expiration is evaluated when the library is loaded and when the setting changes; there is no background deletion task.
- Expired media is deleted before its catalog entry is removed. If catalog persistence fails, the next maintenance pass can reconcile the missing media entry.
- When retention removes the currently playing or shared recording, the library stops playback or dismisses the share sheet and invalidates pending file lookups so a stale asynchronous result cannot reopen deleted media.
- The catalog accepts only unique UUID identifiers, known lowercase audio-container extensions, positive bounded byte counts, finite bounded durations and finite import timestamps. Extensions are never used to construct paths until allowlisted.
- On the first catalog save, the service seeds `recordings.json.backup` with the initial valid catalog. Before each later replacement, it atomically stores the previous last-known-good contents as the backup. If the primary catalog cannot be decoded or validated, the backup is validated and restored.
- If both catalog copies are invalid, the library fails closed and leaves audio files untouched; it does not silently create an empty catalog that could orphan user recordings.
- On library maintenance, abandoned staging contents are removed. UUID-named audio files not referenced by the validated catalog are removed from the managed recordings directory. Unknown filenames and extensions are left untouched.
- The Swift core package tests cover retention boundaries. The app-target XCTest suite exercises catalog recovery, fail-closed behavior, retention deletion and filesystem maintenance on an isolated temporary storage root. Simulator tests do not replace physical-device validation.
