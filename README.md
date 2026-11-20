# iOS SIM Call Recorder

An evidence-driven iOS project exploring lawful, user-consented ways to retain call audio on iPhone. The project does not claim that a third-party iOS app can directly read the private live audio stream of Apple's Phone app.

> **Pre-release / research status.** The repository contains a SwiftUI companion/import app and an executable app-owned Twilio Conference backend. It is not a production-ready universal SIM-call recorder. No physical-device/carrier capture route is certified, no live Twilio account call has been verified, and no cloud environment has been provisioned.

## Product boundary

The project distinguishes five pathways:

| Pathway | Intended role | Current evidence boundary |
|---|---|---|
| Apple Phone native recording | User starts Apple's system recording, then exports audio for import | Availability depends on iOS version, region, language and platform policy. The app does not access Phone.app private storage or live audio. |
| Native SIM-call merge | User merges an existing carrier call with a provider leg, if iOS/carrier topology permits | Not physically verified. Carrier/device/plan-specific; merge and two-channel attribution remain open. |
| App-owned Twilio Conference | Service calls both participants after independent DTMF consent, then records a provider Conference | Backend code exists for consent, Conference callbacks, dual-channel media retrieval and retention. No live account acceptance. Both participants answer separate provider calls; this is not native SIM-call capture. |
| External hardware | Capture speakerphone or an audio/accessory output independently, then import the file | Hardware-specific; no accessory is certified until repeatable physical tests pass. |
| App-owned VoIP | Record media for calls whose media pipeline is owned by this app | Separate product pathway; it does not record native Phone.app cellular calls. |

ReplayKit and microphone APIs are not treated as a way to obtain the private downlink audio of a native cellular Phone call. CallKit provides call integration/system UI, not permission to intercept Phone.app audio. Accessibility audio injection is not a recording API.

## Current implementation

- **Swift core and iOS companion:** user-mediated audio import, app-private storage, opaque catalog, local playback/seeking, interruption and route handling, share/export, retention and recovery.
- **Import validation:** RIFF/WAV chunk boundaries, physical EOF checks, bounded decoding and catalog-recovery regression tests.
- **iOS hardening:** VoiceOver announcements, Dynamic Type, foreground recovery, low-storage preflight, complete file protection and bundled PrivacyInfo.xcprivacy.
- **Backend session API:** authenticated tenant-scoped create/read/cancel, PostgreSQL persistence and ordered migrations.
- **Twilio provider runtime:** outbound DTMF consent calls, account-bound signed call-status/Conference/Recording callbacks, recording-from-start Conference participant creation/addition, provider reconciliation and call cancellation on decline/cancel.
- **Privacy/data:** AES-GCM tenant-scoped participant address vault, authenticated provisioning/deletion API and metadata-only audit records.
- **Media:** RequestedChannels=2 recording retrieval, bounded WAV validation, activity verification in both stereo channels, explicit two-party channel mapping, KMS-backed S3 storage and retryable provider/object retention deletion.
- **Operations:** standalone outbox and retention worker entry points; AWS ECS/RDS/S3/KMS/ALB Terraform and a manual GitHub OIDC deployment workflow; repository CI workflows run on every PR.

The Twilio implementation is an app-owned outbound two-party Conference, not proof that a user's existing SIM call can be merged or captured. CI uses deterministic fake provider resources and synthetic audio fixtures; it does not make live PSTN calls. AWS infrastructure and deployment automation are source artifacts only and have not been applied.

## Evidence policy

Every capability claim must be tied to an exact implementation version and evidence tier:

1. **Static:** source, API and documentation review.
2. **Unit:** deterministic isolated tests.
3. **Integration:** multiple components with controlled dependencies.
4. **Simulator:** app and OS simulator behavior.
5. **Physical device:** exact iPhone model and iOS build.
6. **Carrier verified:** exact carrier, plan, SIM, network and call topology.
7. **Live provider:** real Twilio account, consented PSTN calls, callback ordering, recording retrieval and deletion.

Positive physical configurations require at least three repeated runs and independent verification that both local and remote speech are intelligible. Results are scoped to the tested compatibility tuple; they are not generalized to all iPhones or carriers. A simulator or mocked provider pass is not physical capture evidence.

## Consent, privacy and safety

- Keep TWILIO_ENABLED=false until a launch jurisdiction and disclosure are approved by counsel and a controlled provider test is authorized.
- Only affirmative DTMF 1 is accepted; empty input, other digits and terminal calls without stored consent fail closed.
- Consent call SIDs and Conference participant call SIDs are stored separately. Ambiguous provider outcomes are not blindly retried.
- The current media path accepts exactly two participants and requires activity in both stereo channels. This is not speaker biometrics.
- Never commit raw call recordings, phone numbers, contact names, signed recording URLs, provider tokens or private call content.
- Unsupported, unavailable and unverified pathways remain explicitly labeled; no private API, jailbreak or covert interception route is part of the production target.

## Repository workflow

- Read [AGENTS.md](AGENTS.md) before contributing; it defines branch, security, privacy, test and evidence requirements.
- Work on a task-scoped branch and submit a pull request. Do not push directly to main or bypass protected-branch requirements.
- Use the [bug report form](https://github.com/mojtaba-arvin/ios-sim-call-recorder/issues/new?template=bug_report.yml) for reproducible defects and the [capture evidence form](https://github.com/mojtaba-arvin/ios-sim-call-recorder/issues/new?template=capture_pathway_evidence.yml) for sanitized physical-device results. Never attach raw recordings or personal call data.
- Record the exact PR head SHA and inspect individual test results. A queued, cancelled, skipped or stale run is not a pass.
- Keep platform research, implementation and physical-device evidence separate.

## Roadmap and validation

- [Executable delivery roadmap](docs/engineering/executable-product-roadmap.md)
- [Product validation and go/no-go plan](docs/research/product-validation.md)
- [Twilio bridge unit economics](docs/research/unit-economics.md)
- [Remote physical-device validation kit](docs/validation/remote-device-validation-kit.md)
- [Customer discovery and paid-pilot kit](docs/validation/customer-discovery-kit.md)
- [Counsel-ready legal brief](docs/legal/counsel-brief.md)
- [Physical-device acceptance protocol](docs/engineering/physical-device-test-protocol.md)
- [Security threat model](docs/security/threat-model.md)
- [Operations runbook](docs/operations/runbook.md)

## Project maturity

There is no production release or universal cellular recording guarantee. Release requires a consent-compliant user journey, repeatable physical-device evidence for each advertised pathway, live provider/media acceptance where applicable, legal approval, privacy controls, rollback and a documented compatibility matrix.

Release numbering and first-release gates are defined in [the versioning policy](docs/release/versioning.md); the [changelog](CHANGELOG.md) records the current unreleased state. No version tag is created until the release gates are met.

See the repository [license](LICENSE) for reuse terms.
