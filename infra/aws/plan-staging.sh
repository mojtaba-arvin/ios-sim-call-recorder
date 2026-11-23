#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

: "${EXPECTED_AWS_ACCOUNT_ID:?Set EXPECTED_AWS_ACCOUNT_ID to the approved staging account ID}"
: "${AWS_REGION:?Set AWS_REGION to the approved staging region}"
TFVARS="infra/aws/terraform.tfvars"

command -v aws >/dev/null 2>&1 || { echo "aws CLI is required" >&2; exit 1; }
command -v terraform >/dev/null 2>&1 || { echo "Terraform is required" >&2; exit 1; }
test -f "$TFVARS" || { echo "Missing $TFVARS; copy the example and fill reviewed non-secret identifiers" >&2; exit 1; }

ACTUAL_ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
if [[ "$ACTUAL_ACCOUNT" != "$EXPECTED_AWS_ACCOUNT_ID" ]]; then
  echo "Refusing plan: active AWS account $ACTUAL_ACCOUNT does not match EXPECTED_AWS_ACCOUNT_ID" >&2
  exit 1
fi

export TF_IN_AUTOMATION=true
export AWS_PAGER=""

PLAN_FILE="$(mktemp "${TMPDIR:-/tmp}/ios-sim-call-recorder-staging-plan.XXXXXX")"
cleanup() { rm -f "$PLAN_FILE"; }
trap cleanup EXIT

terraform -chdir=infra/aws init -backend=false -input=false
terraform -chdir=infra/aws fmt -check -recursive
terraform -chdir=infra/aws validate
terraform -chdir=infra/aws plan \
  -input=false \
  -lock-timeout=60s \
  -var-file=terraform.tfvars \
  -out="$PLAN_FILE"
terraform -chdir=infra/aws show -no-color "$PLAN_FILE"

echo "PLAN ONLY: no terraform apply/destroy command was run. Temporary plan file removed on exit."
