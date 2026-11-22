#!/usr/bin/env bash
set -euo pipefail

REPOSITORY="${REPOSITORY:-mojtaba-arvin/ios-sim-call-recorder}"
RULESET_ID="${RULESET_ID:-27591151}"

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required." >&2
  exit 1
fi
gh auth status >/dev/null

echo "Applying required PR and CI rules to main in ${REPOSITORY} (ruleset ${RULESET_ID})."
gh api --method PUT "repos/${REPOSITORY}/rulesets/${RULESET_ID}" --input - <<'JSON'
{
  "name": "protect main",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/main"],
      "exclude": []
    }
  },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "required_linear_history" },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": true
      }
    },
    { "type": "required_conversation_resolution" },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          { "context": "backend-postgres (PostgreSQL 16)" },
          { "context": "backend-postgres (PostgreSQL 17)" },
          { "context": "swift-core" },
          { "context": "xctest (iPhone 16)" },
          { "context": "xctest (iPhone 16 Pro)" },
          { "context": "audio-analyzer" },
          { "context": "terraform-validate" },
          { "context": "repository-policy" }
        ]
      }
    }
  ]
}
JSON

echo "Ruleset updated. Verify it with:"
echo "gh api repos/${REPOSITORY}/rulesets/${RULESET_ID}"
