# AWS staging plan-only checklist

**Current status:** BLOCKED-ACCESS — no AWS account, credentials, approved account ID, VPC/subnets, ACM certificate, DNS name, application secret or OIDC role were supplied/verified in this session. No AWS API call, plan, resource creation or spend is claimed.

## Why a plan-only script exists

`infra/aws/plan-staging.sh` performs an identity guard, backendless initialization, formatting/validation and a read-only Terraform plan. It never invokes `apply` or `destroy`; its temporary plan file is removed on exit. It requires the operator to explicitly identify the expected AWS account to prevent planning against an unintended account.

## Preconditions

1. An approved, dedicated staging AWS account and region.
2. AWS CLI credentials with read permissions sufficient for Terraform refresh/data sources; no create/update permissions are needed for the plan itself.
3. `EXPECTED_AWS_ACCOUNT_ID` set to the exact approved 12-digit account ID.
4. `AWS_REGION` set to the approved region.
5. `infra/aws/terraform.tfvars` created locally from `terraform.tfvars.example`; no secrets, phone numbers, tokens or key material in the file.
6. Valid VPC ID, at least two public and two private subnet IDs across AZs, ACM certificate ARN, HTTPS public origin, Secrets Manager application secret ARN and GitHub OIDC provider ARN.
7. Cost estimate reviewed before any future apply decision. The stack includes ALB, RDS, ECS, ECR, WAF, KMS, S3 and CloudWatch and may incur charges after deployment.

## Run

From repository root:

```sh
cp infra/aws/terraform.tfvars.example infra/aws/terraform.tfvars
# Fill reviewed infrastructure identifiers locally; do not commit terraform.tfvars.
export EXPECTED_AWS_ACCOUNT_ID=123456789012
export AWS_REGION=eu-central-1
./infra/aws/plan-staging.sh
```

Replace the example account ID only with the separately approved staging account. The script calls `aws sts get-caller-identity` and refuses to continue on a mismatch.

## Review the plan

- Confirm only the intended `staging` environment and region are addressed.
- Confirm `enable_live_twilio = false`.
- Confirm worker and retention desired counts are zero while live Twilio is disabled.
- Review IAM trust and least privilege, KMS key policy, private RDS networking, S3 public access block, retention lifecycle, ALB/WAF and log retention.
- Review DB deletion protection and final snapshot behavior; the current Terraform source has `deletion_protection = false` and `skip_final_snapshot = true`, which must be explicitly reviewed before any apply.
- Review WAF managed-rule behavior and the 2,000/IP/5-minute default threshold against expected provider callback bursts.
- Estimate monthly spend with the AWS Pricing Calculator and obtain a separate written budget approval.

## Hard stop

A successful Terraform `validate` or `plan` is not an AWS deployment. Do not run `terraform apply`, create resources, deploy ECS, run migrations against a real database, or enable Twilio from this script. Those require a separate explicit authorization and reviewed change plan.
