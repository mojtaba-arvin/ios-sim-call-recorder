#!/usr/bin/env bash
set -euo pipefail

REPOSITORY="${REPOSITORY:-mojtaba-arvin/ios-sim-call-recorder}"
RULESET_ID="${RULESET_ID:-27591151}"
PAYLOAD="${PAYLOAD:-docs/governance/main-ruleset-payload.json}"

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required." >&2
  exit 1
fi
gh auth status >/dev/null
test -f "$PAYLOAD" || { echo "Missing canonical Ruleset payload: $PAYLOAD" >&2; exit 1; }

echo "Applying canonical main Ruleset payload to ${REPOSITORY} (ruleset ${RULESET_ID})."
gh api --method PUT "repos/${REPOSITORY}/rulesets/${RULESET_ID}" --input "$PAYLOAD"

echo "Ruleset update requested. Verify the live state with:"
echo "gh api repos/${REPOSITORY}/rulesets/${RULESET_ID}"
