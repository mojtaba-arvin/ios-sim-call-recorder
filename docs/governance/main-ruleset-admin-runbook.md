# Admin runbook — protect main Ruleset

**Repository:** `mojtaba-arvin/ios-sim-call-recorder`  
**Ruleset:** `protect main`, ID `27591151`  
**Last verified read-back:** 2026-11-24 (GitHub API).

## Current live state

The Ruleset is **active** and targets only `refs/heads/main`. Its bypass actor list is empty, and the connected identity cannot bypass it.

The live Ruleset read-back confirms these rules:

- `deletion`
- `non_fast_forward`
- `required_linear_history`
- `pull_request`, with `required_review_thread_resolution: true`
- `required_status_checks`, with strict up-to-date enforcement

The eight required status contexts are exactly:

- `backend-postgres (PostgreSQL 16)`
- `backend-postgres (PostgreSQL 17)`
- `swift-core`
- `xctest (iPhone 16)`
- `xctest (iPhone 16 Pro)`
- `audio-analyzer`
- `terraform-validate`
- `repository-policy`

There is no standalone `required_conversation_resolution` rule. Review-thread resolution is configured under the `pull_request` rule.

## Historical application notes

The JSON payload in `main-ruleset-payload.json` is the canonical desired configuration. The original administrator handoff is historical: the Ruleset was subsequently applied and its live state was verified. Do not rerun an administrative mutation merely because this runbook exists.

To inspect the current configuration without changing it:

```sh
gh api repos/mojtaba-arvin/ios-sim-call-recorder/rulesets/27591151
```

If the live read-back ever differs from the assertions above, stop merges and reconcile the actual state before proceeding. Do not create a duplicate Ruleset or bypass protection.

## Merge protocol

- Merge only after all eight required checks pass on the exact current PR head.
- Ensure the PR is mergeable and has no unresolved review threads.
- Use squash merges to preserve the linear main history.
- After each merge, update remaining PR branches with the new main and rerun exact-head checks.

## Evidence and release boundary

The Ruleset read-back proves repository governance only. It does not prove physical iPhone/SIM/carrier behavior, live Twilio acceptance, AWS deployment, customer validation, or legal/privacy approval. Those remain separate release gates.


**Freshness rule:** Treat the read-back above as a dated snapshot; re-read the live Ruleset before any future governance change or merge campaign.
