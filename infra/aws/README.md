# AWS staging deployment

This directory contains Terraform for an isolated AWS staging environment:
Application Load Balancer (HTTPS), ECS Fargate API/worker/retention services,
private PostgreSQL RDS, encrypted S3 media storage, KMS, Secrets Manager,
CloudWatch logs/alarms, ECR and GitHub Actions OIDC deployment.

## Safety defaults

- `enable_live_twilio = false` by default. The API therefore does not enqueue
  outbound consent calls and worker/retention desired counts remain zero.
- No Twilio credentials, API token hashes, participant-address key or database
  password belong in Terraform variables, tfvars, Git or GitHub repository
  variables. Inject them through the referenced Secrets Manager JSON secret.
- Public ingress is HTTPS only; HTTP redirects to HTTPS. The database is private.
- The S3 bucket blocks public access and uses a customer-managed KMS key.
- ECS deployments use the deployment circuit breaker with rollback enabled.
- This stack is not free: ALB, RDS, ECS, NAT/egress, KMS, S3 and CloudWatch can
  incur charges. Review the AWS Pricing Calculator and budget alarms before apply.

## Prerequisites

1. An AWS account with a VPC, at least two public subnets and two private
   subnets across availability zones.
2. An ACM certificate for a hostname you control and a DNS record pointing that
   hostname to the resulting ALB.
3. A GitHub Actions OIDC provider already registered in IAM:
   `https://token.actions.githubusercontent.com`, audience
   `sts.amazonaws.com`.
4. A Secrets Manager JSON secret containing at minimum
   `BRIDGE_API_TOKEN_HASHES`. When enabling live Twilio, also provide
   `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, optional API key/secret,
   `TWILIO_PROVIDER_ACCOUNT_ID`, `TWILIO_FROM_NUMBER`,
   `TWILIO_CONSENT_POLICY_VERSION`, `TWILIO_CONSENT_DISCLOSURE`, and
   `PARTICIPANT_ADDRESS_KEY_HEX` (32 random bytes encoded as 64 hex chars).
5. Terraform >=1.6 and AWS credentials with permissions to create the listed
   resources.

## Bootstrap

Copy `terraform.tfvars.example` to `terraform.tfvars`, fill infrastructure
identifiers, and leave `enable_live_twilio = false`.

```sh
terraform -chdir=infra/aws init
terraform -chdir=infra/aws fmt -check
terraform -chdir=infra/aws validate
terraform -chdir=infra/aws plan
```

Review the plan and estimated monthly cost. Only then apply:

```sh
terraform -chdir=infra/aws apply
```

The RDS database secret is created by Terraform. The application secret is
created/managed separately by the operator. The output
`github_deploy_role_arn` is the IAM role for GitHub OIDC; add it as the
repository Actions secret `AWS_ROLE_ARN`. Add repository variables
`AWS_REGION`, `ECR_REPOSITORY`, `ECS_CLUSTER`, `ECS_API_SERVICE`,
`ECS_WORKER_SERVICE`, `ECS_RETENTION_SERVICE`, and `STAGING_API_URL`
from Terraform outputs.

The public hostname must resolve to the ALB and match the ACM certificate and
`public_origin`. Do not enable `TWILIO_ENABLED` until the consent disclosure
has legal approval and the live provider/carrier tests are authorized.

## Deploy

The `Deploy staging` workflow is manual. It builds and pushes the backend
image, runs ordered database migrations as a one-off ECS task, updates the API
service, waits for stability, then performs an authenticated-independent
readiness check. Worker and retention services are only started if Terraform
was applied with `enable_live_twilio = true`.

## Current state

Terraform and deployment automation are source artifacts only. No AWS account,
VPC, certificate, DNS, Secrets Manager secret or cloud resources were provisioned
from this session; no spend was incurred. The stack must pass `terraform
validate` and an operator-reviewed plan before deployment.
