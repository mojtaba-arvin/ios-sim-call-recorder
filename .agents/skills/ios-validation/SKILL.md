---
name: ios-validation
description: Validate iOS app changes using exact-head builds and tests, with clear separation between unit, simulator, physical-device, and carrier evidence.
---

# iOS validation

## Procedure
1. Record the exact PR head SHA, Xcode version, macOS runner, iOS SDK/runtime and selected simulator.
2. Generate the project from project.yml; do not hand-edit generated Xcode project files.
3. Run focused Swift package tests and app-hosted XCTest tests relevant to the change.
4. Run the full applicable Simulator suite and inspect the test result summary, not only the workflow conclusion.
5. Verify observer, task, file-handle, security-scope and AVAudioSession lifecycle cleanup where relevant.
6. For file-format validation, include adversarial fixtures whose container metadata claims bytes beyond physical EOF; do not assume AVFoundation decoder EOF behavior detects truncation. For RIFF/WAV, validate RIFF and chunk boundaries against actual file size before decode.
7. Ensure a regression test fails on the prior implementation before accepting the fix. Inspect individual XCTest failures even when the Swift package workflow is green.
8. For audio features, test interruption, route changes, seek, completion, cancellation and repeated start/stop.
9. Record simulator limitations. Do not infer Phone.app audio access, carrier merge behavior or hardware compatibility from Simulator.
10. Physical-device runs must record exact model identifier, iOS version/build, region/country/language, carrier, SIM, network, call direction, route and accessory firmware.
11. Exercise failure cleanup at every adapter boundary: partial prepare, consent rejection, connect failure, capture-start failure, cancellation race and finalization failure. Assert idempotent cleanup and verify no late completion can reactivate a terminal session.
12. Require three repeated runs for each claimed positive physical configuration and verify both speech directions.

## Output
- Exact SHA, commands, environment and test counts.
- Unit/integration/simulator evidence.
- Physical-device/carrier evidence only when actually collected.
- Failures, flaky tests and untested cases.

## Completion gate
The report must not claim a higher evidence tier than the environment actually exercised.
