# iOS SIM Call Recorder

An evidence-driven iOS project exploring lawful, user-consented ways to retain cellular-call audio on iPhone. The project is intentionally conservative: it does not claim that a third-party iOS app can directly read the private live audio stream of Apple's Phone app.

> **Pre-release / research status.** The repository now contains a runnable SwiftUI companion app and a tested provider-neutral backend foundation, but it is not a production-ready universal SIM-call recorder. No physical-device/carrier capture route is currently certified.

## Product boundary

The project distinguishes four separate pathways:

| Pathway | Intended role | Current evidence boundary |
|---|---|---|
| Apple Phone native recording | User starts Apple's system recording, then exports the resulting audio for import | Availability depends on iOS version, region, language and platform policy. The app does not access Phone.app private storage or its live audio stream. |
| Carrier conference bridge | Join a cellular call to a separately hosted conference/recording service | Backend lifecycle and persistence foundations exist. Real provider integration, carrier merge topology, two-way audio and channel behavior remain unverified. |
| External hardware | Capture speakerphone or an audio/accessory output independently, then import the file | Hardware-specific; no accessory is certified until repeatable physical tests pass. |
| App-owned VoIP | Record media for calls whose media pipeline is owned by this app | Separate product pathway; it does not record native Phone.app cellular calls. |

ReplayKit and microphone APIs are not treated as a way to obtain the private downlink audio of a native cellular Phone call. CallKit provides call integration/system UI, not permission to intercept Phone.app audio. Accessibility audio injection is not a recording API.

## Current implementation

- **Swift core:** capability/context types, consent-gated session lifecycle, cancellation and adapter resource cleanup.
- **iOS companion app:** user-mediated document import, app-private storage, opaque local catalog, local playback/seeking, interruption and output-route handling, system share/export, opt-in retention and catalog recovery.
- **Import validation:** container probing, metadata limits, and full decode/boundary hardening are covered by dedicated regression tests; check the exact mainline CI status before relying on the newest hardening change.
- **Audio validation tooling:** local WAV signal metrics and deterministic regression fixtures.
- **Conference bridge backend:** provider-neutral session state machine, participant consent gate, Twilio webhook signature verifier, PostgreSQL persistence, transactional outbox, leased dispatcher, provider-resource mappings and reconciliation contracts.
- **Engineering workflow:** role contracts, reusable research/validation/security skills, task/review templates and machine-checked task/evidence policies are being consolidated into the mainline.

The backend is a foundation, **not a deployable recording service**. It does not yet include authenticated HTTP session endpoints, a concrete live provider command adapter, a supervised production worker, media ingestion/object storage, audio verification or provider/product deletion reconciliation.

## Evidence policy

Every capability claim must be tied to an exact implementation version and evidence tier:

1. **Static:** source, API and documentation review.
2. **Unit:** deterministic isolated tests.
3. **Integration:** multiple components with controlled dependencies.
4. **Simulator:** app and OS simulator behavior.
5. **Physical device:** exact iPhone model and iOS build.
6. **Carrier verified:** exact carrier, plan, SIM, network and call topology.

Positive physical configurations require at least three repeated runs and independent verification that both local and remote speech are intelligible. Results are scoped to the tested compatibility tuple; they are not generalized to all iPhones or carriers. A simulator or mocked provider pass is not physical capture evidence.

## Consent, privacy and safety

- Recording is permitted only where lawful and with the required participant notice and consent.
- Consent evidence must be verified by a trusted component; a UI checkbox or non-empty string is not proof.
- Never commit raw call recordings, phone numbers, contact names, signed recording URLs, provider tokens or private call content.
- Test audio is generated locally. Physical-device evidence published to the repository must contain only sanitized metadata and metrics.
- Unsupported, unavailable and unverified pathways must remain explicitly labeled; no private API, jailbreak or covert interception route is part of the production target.

## Repository workflow

- Read [AGENTS.md](AGENTS.md) before contributing; it defines branch, security, privacy, test and evidence requirements.
- Work on a task-scoped branch and submit a pull request. Do not push directly to `main`, force-push shared branches or merge without owner authorization.
- Use the [bug report form](https://github.com/mojtaba-arvin/ios-sim-call-recorder/issues/new?template=bug_report.yml) for reproducible defects and the [capture evidence form](https://github.com/mojtaba-arvin/ios-sim-call-recorder/issues/new?template=capture_pathway_evidence.yml) for sanitized physical-device results. Never attach raw recordings or personal call data.
- Record the exact PR head SHA and inspect the individual test results. A queued, cancelled, skipped or stale run is not a pass.
- Keep platform research, implementation and physical-device evidence separate. Link compatibility claims to the exact evidence that supports them.

## Project maturity

This repository is under active engineering. There is no production release or universal cellular recording guarantee. The release gate is a complete, consent-compliant user journey with repeatable physical-device evidence for each advertised pathway, plus tested failure recovery, privacy controls and a documented compatibility matrix.

Release numbering and first-release gates are defined in [the versioning policy](docs/release/versioning.md); the [changelog](CHANGELOG.md) records the current unreleased state. No version tag is created until the release gates are met.

See the repository [license](LICENSE) for reuse terms.
