# Admin runbook — protect main Ruleset

**Target:** repository `mojtaba-arvin/ios-sim-call-recorder`, existing Ruleset ID `27591151` (`protect main`).  
**Current read-back:** active; target `~DEFAULT_BRANCH`; only `deletion` and `non_fast_forward`; bypass actors empty.  
**Required outcome:** main only, pull requests, linear history, review-thread resolution and all eight stable Release Preflight checks. Do not create a duplicate ruleset.

## Why this is an admin handoff

The connected GitHub surface can GET the Ruleset but does not expose a supported PUT/PATCH action. This document and the adjacent JSON are a prepared patch, not an applied change.

## Preconditions

1. Confirm you are an authorized repository administrator.
2. Review `main-ruleset-payload.json` against the current ruleset read-back.
3. Ensure the eight check names are present in the canonical `.github/workflows/release-preflight.yml`.
4. Apply during a controlled maintenance window. Existing in-flight PRs may need fresh runs after enforcement.
5. Do not add bypass actors for routine development.

## Apply

From a trusted terminal with GitHub CLI authenticated as a repository administrator:

```sh
gh auth status
gh api --method PUT repos/mojtaba-arvin/ios-sim-call-recorder/rulesets/27591151 \
  --input docs/governance/main-ruleset-payload.json
```

This updates the existing Ruleset ID; it does not create a second ruleset.

## Mandatory read-back

```sh
gh api repos/mojtaba-arvin/ios-sim-call-recorder/rulesets/27591151 \
  > /tmp/ios-sim-call-recorder-main-ruleset-readback.json
```

Verify all of the following from the returned JSON:

- `id == 27591151`, `name == protect main`, `enforcement == active`.
- `conditions.ref_name.include` contains only `refs/heads/main`.
- `bypass_actors == []`.
- Rules include `deletion`, `non_fast_forward`, `required_linear_history`, `pull_request`, and `required_status_checks`.
- The `pull_request.parameters.required_review_thread_resolution` value is `true`.
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

Conversation resolution is configured as the `required_review_thread_resolution` parameter of the `pull_request` rule. It is not a standalone Ruleset rule type.

If any assertion fails, stop and reconcile the payload with the actual current Ruleset; do not create a second ruleset or claim success.

## Evidence to attach to Issue #56

Attach the sanitized GET read-back JSON and timestamp, plus administrator authorization evidence appropriate for the private audit trail. Do not include tokens. Close Issue #56 only after all rule assertions pass.
