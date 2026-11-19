# Recording import boundary

**Status:** core validation contract implemented; iOS app-shell integration is not yet present.

## Product flow

1. The user exports a recording from Apple Notes or an external recorder and explicitly selects this app through the share sheet or Files picker.
2. The app obtains a temporary document URL from the system document picker.
3. The app accesses the URL only while its security-scoped access is active (where required).
4. The app copies the selected file into a private staging directory. It does not read Notes' private database or attempt to automate Phone.app.
5. A platform media adapter probes the actual container, duration, sample rate, channel count and file size. The extension is only a hint and must not be treated as proof of media type.
6. RecordingImportValidator checks the probed metadata before the file is accepted into the recording library.
7. The app moves the validated file atomically into app-managed storage, applies the retention policy, and removes staging data on success or failure.

## Core validation contract

RecordingImportMetadata contains only the filename, byte count, duration, sample rate, channel count, recognized container and user-selected import source. It intentionally excludes phone numbers, contact names, transcripts, call participant identities and audio bytes.

The initial conservative limits are:

- Non-empty file, at most 500 MiB.
- Positive finite duration, at most 24 hours.
- Sample rate from 8 kHz through 192 kHz.
- One or two audio channels.
- Recognized containers: M4A, MP3, WAV, CAF and AIFF.
- The probed container must agree with the filename extension.

These are ingestion safety bounds, not claims that every listed format is produced by Apple Notes or supported by every accessory. The platform adapter must fail closed when it cannot inspect the real media container.

## Security and privacy requirements for the app shell

- Do not log file URLs, original filenames, contact names, phone numbers, transcripts, or media payloads.
- Use opaque generated identifiers for imported assets and diagnostic events.
- Do not upload recordings automatically. Any remote processing requires a separate explicit user action and consent flow.
- Keep temporary copies in app-private storage; clean them on cancellation, validation failure, and import failure.
- Enforce a storage quota and a user-visible retention/deletion policy before shipping.
- Do not claim that an imported file contains both sides of a call solely because its metadata is valid. Two-way speech verification is a separate quality gate.
- Keep user-mediated Apple Phone recording distinct from app-owned VoIP and carrier conference recording.

## Current implementation boundary

The Swift package now provides a platform-independent metadata validator and deterministic tests. It does not yet provide a SwiftUI/UIKit document picker, security-scoped URL handling, AVFoundation probing, durable media storage, waveform analysis or speech-direction verification. Those belong in the app-shell/integration layer after the application target and deployment configuration are established.

## Next engineering steps

1. Establish the iOS app target and supported deployment baseline without weakening the reusable core package's testability.
2. Implement a document-picker adapter with security-scoped access and cancellation-safe staging.
3. Implement an AVFoundation metadata probe and verify actual file types, not extensions alone.
4. Add integration tests with generated synthetic audio fixtures; never commit real calls or personal recordings.
5. Add explicit retention, deletion and optional transcription policies.
6. Add a separate two-way audio QA workflow with synthetic known-speaker fixtures and later physical-device evidence.
