# Admin runbook — protect main Ruleset

**Target:** repository `mojtaba-arvin/ios-sim-call-recorder`, existing Ruleset ID `27591151` (`protect main`).  
**Current read-back:** active; target `~DEFAULT_BRANCH`; only `deletion` and `non_fast_forward`; bypass actors empty.  
**Required outcome:** main only, pull requests, linear history, conversation resolution and all eight stable Release Preflight checks. Do not create a duplicate ruleset.

## Why this is an admin handoff

The connected GitHub surface can GET the Ruleset but does not expose a supported PUT/PATCH action. Repository metadata reports admin permission, but the integration's callable API surface remains read-only for Rulesets. This document and the adjacent JSON are a prepared patch, not an applied change.

## Preconditions

1. Confirm you are an authorized repository administrator.
2. Review `main-ruleset-payload.json` against the current ruleset read-back.
3. Ensure the eight check names are present in the canonical `.github/workflows/release-preflight.yml`.
4. Apply during a controlled maintenance window. This will enforce required checks for new PRs to main; existing in-flight PRs may need a fresh run.
5. Do not add bypass actors for routine development.

## Apply

From a trusted terminal with GitHub CLI authenticated as a repository administrator:

```sh
gh auth status
gh api --method PUT repos/mojtaba-arvin/ios-sim-call-recorder/rulesets/27591151 \
  --input docs/governance/main-ruleset-payload.json
```

The request updates the existing Ruleset ID. It does not create a new Ruleset.

## Mandatory read-back

```sh
gh api repos/mojtaba-arvin/ios-sim-call-recorder/rulesets/27591151 \
  > /tmp/ios-sim-call-recorder-main-ruleset-readback.json
```

Verify all of the following from the returned JSON (do not rely on the command's exit code alone):

- `id == 27591151`, `name == protect main`, `enforcement == active`.
- `conditions.ref_name.include` contains only `refs/heads/main`.
- `bypass_actors == []`.
- Rules include `deletion`, `non_fast_forward`, `required_linear_history`, `pull_request`, `required_conversation_resolution`, `required_status_checks`.
- `required_status_checks.strict_required_status_checks_policy == true`.
- Required contexts exactly include:
  - `backend-postgres (PostgreSQL 16)`
  - `backend-postgres (PostgreSQL 17)`
  - `swift-core`
  - `xctest (iPhone 16)`
  - `xctest (iPhone 16 Pro)`
  - `audio-analyzer`
  - `terraform-validate`
  - `repository-policy`
- Do not require path-filtered `Backend staging integration` globally.

If any assertion fails, stop and reconcile the payload with the actual current Ruleset; do not create a second ruleset or claim success.

## Evidence to attach to Issue #56

Attach the sanitized GET read-back JSON and timestamp, administrator identity/authorization evidence appropriate for the private audit trail, and a screenshot or export showing the active Ruleset. Do not include tokens. Close Issue #56 only after all rule assertions pass.
