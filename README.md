# iOS SIM Call Recorder

Research and engineering project exploring lawful, consent-based recording workflows for ordinary carrier (SIM/PSTN) calls on iPhone.

## Project objective

Investigate and validate multiple independent recording pathways across iPhone hardware, iOS builds, regions, carriers, SIM configurations and audio routes. The goal is evidence-backed compatibility coverage—not an unsupported promise that every iPhone can be recorded by an app-only implementation.

## Current status

- [x] Initial technical pathway matrix and compatibility dimensions documented.
- [ ] Validate conference-bridge feasibility with real carriers and devices.
- [ ] Prototype Bluetooth HFP accessory-side capture.
- [ ] Establish native iOS recording companion/import feasibility.
- [ ] Build carrier capability and regional evidence registers.
- [ ] Define and implement the first production pathway after a real-device proof.

See [the research matrix](docs/research/recording-pathways.md) for pathway analysis, constraints, acceptance gates and references.

## Important platform distinction

CallKit supports calls managed by an app; it is not a public API for intercepting audio from Apple's native Phone app. Native iOS call recording is region-dependent and does not establish a general third-party live-audio API. Hardware, carrier and conference-bridge approaches must be evaluated independently.

## Engineering principles

1. No direct commits to `main`; all work uses short-lived topic branches and pull requests.
2. Every capability claim must cite primary evidence or a reproducible physical-device test.
3. Compatibility is recorded as a tuple of device, OS build, region, carrier, SIM, network, call scenario, route and pathway.
4. Consent, disclosure, privacy, retention and deletion are product requirements, not optional polish.
5. Experimental/private-API/jailbreak work stays isolated from production and App Store targets.
6. A pathway is not supported until it passes the documented acceptance gates.

## Repository layout

- `docs/research/` — technical feasibility, evidence and compatibility research.
- `docs/engineering/` — architecture decisions, development workflow and test strategy.
- `.github/` — pull request templates and CI automation.
- `scripts/` — repository validation utilities.

## Development status

The repository is currently in the research and proof-of-feasibility phase. Do not infer that an iOS app, recording backend, accessory firmware or carrier integration is implemented until corresponding source code and tests exist.
