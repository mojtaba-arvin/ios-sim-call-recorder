# Recording import boundary

**Status:** implemented in the iOS app target. The core metadata validator, document importer, security-scoped access, coordinated staging copy, AVFoundation probe/decode, private catalog, playback/export, retention and recovery are integrated. See [the app shell implementation](ios-app-import-shell.md).

## Product flow

1. The user explicitly selects an audio file through the SwiftUI Files document importer.
2. The app starts security-scoped access where required and coordinates the external read with NSFileCoordinator.
3. The source size and available disk capacity are checked before copying. Import fails with an actionable low-storage message when the source plus the configured free-space reserve will not fit.
4. The app copies the file to an opaque UUID staging path in app-private Application Support.
5. A container signature probe and WAV RIFF/chunk-boundary checks validate the actual file structure. AVAudioFile opens the file and decodes the full payload in bounded chunks.
6. The core validator checks file size, duration, sample rate, channel count and extension/container agreement.
7. The validated file is moved into the private recordings directory. Production media and catalog files receive complete file protection; app-managed directories are excluded from device backups.
8. The catalog stores only opaque ID, container, byte count, duration and import timestamp. Original filenames and call content are not persisted.
9. On launch and whenever the app returns to the foreground, maintenance validates/recoveries the catalog, applies retention and removes abandoned staging files and known UUID media orphans. Unknown files are preserved.

## Safety and recovery behavior

- Import is rejected before staging when available capacity is below source size plus the safety reserve.
- A failed copy/decode/validation removes the staging artifact.
- A corrupt primary catalog is restored from a validated backup.
- If both catalog copies are invalid or missing while managed media exists, the service fails closed and preserves the media.
- A process interruption may leave a partial staging file; the next successful foreground maintenance pass removes abandoned staging contents.
- Complete file protection prevents access while the device is locked and keeps protected media unavailable after reboot until the first device unlock. This policy is intentionally stronger than background availability.
- Retention is opt-in (Never, 30, 90 or 365 days) and is applied on library load/foreground refresh and when the setting changes; there is no scheduled background deletion service.

## Validation boundary

The app validates structural integrity and decodability. It does not prove that an imported recording contains both speakers, that channels map to individual participants, or that the file came from an Apple-native cellular recording pathway. Those remain M2/M4 evidence gates.

## Remaining checks

- Run the VoiceOver and Dynamic Type checklist on physical devices and record exact device/iOS tuples.
- Exercise lock/reboot data protection on a physical iPhone, including first-unlock behavior.
- Run low-storage and process-termination scenarios on supported devices.
- Configure an Apple Developer Team, distribution certificate and provisioning profile before a signed Release archive can be produced.
