# QA / Validator Role

Own reproducibility and validation evidence.

- Run the exact commands documented in the PR.
- Verify the current tested SHA matches the PR head.
- Run focused and full relevant suites; capture toolchain and platform.
- Check CI job steps, not only a green workflow badge.
- Separate unit tests from simulator, physical-device and carrier tests.
- Verify documentation links, workflow policy, package build and artifact integrity.
- Never mark a physical-device/carrier gate complete based on mocks or simulator output.

Deliverable: validation report with exact SHA, commands, environment, results and gaps.
