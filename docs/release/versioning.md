# Release and versioning policy

The project has no production release yet. Do not create or advertise a version tag until the release gates below are met.

## Scheme

Use Semantic Versioning `MAJOR.MINOR.PATCH` once the first public release is made.

Before 1.0.0:
- Start at `0.1.0` for the first usable, explicitly limited alpha release.
- Increment MINOR for a new user-visible capability or a meaningful public interface change.
- Increment PATCH for backwards-compatible bug fixes, security fixes and documentation corrections.
- Use prerelease identifiers such as `0.2.0-alpha.1`, `0.2.0-beta.1` and `0.2.0-rc.1` for staged testing.
- Treat breaking changes as a MINOR increment while on 0.x; document migration requirements.

At 1.0.0, public interfaces and advertised compatibility behavior must have a support policy. After 1.0.0:
- MAJOR: incompatible public API, storage format or user-data migration.
- MINOR: backwards-compatible functionality.
- PATCH: backwards-compatible fixes and security updates.

## What constitutes a release

A release tag must point to the exact commit whose required CI checks passed. A release candidate must not be retagged or silently moved.

Before the first alpha:
- A complete app build and automated import/playback/storage regression suite pass on the exact tag candidate.
- No unresolved P0/P1 review finding remains.
- The app's current limitations and non-supported capture paths are visible in release notes.
- User consent, retention, export, deletion and privacy behavior are documented.
- No physical-device/carrier capability is advertised without matching evidence.

Before advertising a cellular capture pathway:
- Run the physical-device protocol for the exact compatibility tuple.
- Verify both speech directions independently.
- Complete at least three positive repetitions for each claimed configuration.
- Publish only sanitized metadata/metrics; keep raw recordings and phone numbers private.
- Label each pathway as Confirmed, Observed, Hypothesis or Rejected.

## Tagging and changelog

- Tags use a leading `v`, for example `v0.1.0-alpha.1`.
- Release tags are annotated and immutable.
- Every release has a dated changelog entry describing capabilities, known limitations, migrations and evidence tier.
- Do not infer the app version from a PR number, commit count or CI run number.
- Keep build metadata separate from the user-facing semantic version.
- No release or tag is created by this policy change.
