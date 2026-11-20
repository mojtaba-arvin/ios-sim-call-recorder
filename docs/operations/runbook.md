# Operations runbook — AWS/Twilio pre-production

**Status:** executable operations template. The provider code and AWS Terraform/deploy workflow exist, but no Twilio calls or AWS resources have been provisioned from this session.

## Safety posture

- Keep TWILIO_ENABLED=false until the selected jurisdiction and disclosure are approved by counsel and a controlled provider test is authorized.
- The Twilio implementation creates two app-owned outbound calls and a provider Conference. It does not capture or merge the user's existing native SIM call.
- Use a dedicated Twilio subaccount and test numbers. Never use personal customer contacts.
- Keep API/provider credentials and the participant-address AES key in Secrets Manager; never in source control, GitHub variables visible to untrusted workflows, issue text or logs.
- Never log request bodies, phone addresses, raw media, signatures, access tokens, provider SIDs or signed media URLs.
- A green process health check is not proof of consent, provider, media, carrier or legal readiness.

## Bootstrap

1. Create a VPC with two public and two private subnets across availability zones.
2. Request an ACM certificate and configure DNS for the chosen staging hostname.
3. Register the GitHub Actions OIDC provider in IAM.
4. Create a Secrets Manager JSON secret with BRIDGE_API_TOKEN_HASHES. For live Twilio, also inject TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PROVIDER_ACCOUNT_ID, TWILIO_FROM_NUMBER, TWILIO_CONSENT_POLICY_VERSION, TWILIO_CONSENT_DISCLOSURE and PARTICIPANT_ADDRESS_KEY_HEX.
5. Copy infra/aws/terraform.tfvars.example to terraform.tfvars, set infrastructure identifiers, keep enable_live_twilio=false, and review estimated monthly cost.
6. Run terraform fmt -check, terraform init -backend=false, terraform validate and terraform plan. Use encrypted remote state for any shared environment.
7. Apply only after the owner approves the plan. Add the Terraform outputs as GitHub Actions secrets/variables and run the manual Deploy staging workflow.
8. Verify /health/ready and CloudWatch logs before enabling any external traffic.

## Migrations and runtime

- Apply migrations in numeric order through 0009_provider_consent_call_resources.sql.
- The API uses RDS-managed connection secret fields in AWS; local Compose may use DATABASE_URL.
- When TWILIO_ENABLED=true, the API mounts /v1/twilio/consent, /v1/twilio/call-status, /v1/twilio/conference and /v1/twilio/recording.
- Provision each participant's E.164 address through authenticated PUT /v1/participants/{ref}/address before creating a session.
- The session API enqueues consent requests transactionally. The outbox worker places calls; the API itself does not make provider calls.
- The retention worker deletes the provider recording and S3 object independently. A deletion is complete only when both are confirmed.
- Twilio dual-channel media retrieval requires RequestedChannels=2. The current path supports exactly two participants and validates activity in both stereo channels.

## Controlled live acceptance

1. Verify the Twilio account, caller ID, outbound destination permissions, recording availability and billing alerts.
2. Use two test participants who have agreed to the exact disclosure.
3. Provision their opaque participant refs and addresses in one isolated tenant.
4. Start one short session. Confirm both consent calls are delivered and no Conference is created until both press 1.
5. Test a decline, empty Gather, no-answer and API cancellation. Confirm no recording-enabled Conference is created and outstanding consent legs are completed.
6. For the affirmative path, confirm the first participant joins, the second is added, recording starts from the Conference start and the signed callbacks map to the correct internal session.
7. Download with RequestedChannels=2. Confirm stereo PCM16, channel 1/2 activity and expected two-party channel mapping. Review the audio privately; do not upload it to GitHub.
8. Trigger retention in a test environment. Verify Twilio recording deletion and S3 object deletion independently, including retry after one side fails.
9. Only then record the provider test as passed. This still does not prove native SIM-call merge.

## Incident response

| Signal | Immediate action | Evidence to preserve |
|---|---|---|
| Authentication spike / token leak | Disable affected token digest and rotate secret; block ingress if needed | Timestamp, tenant ID, route and status counts; never token values |
| Cross-tenant access suspicion | Disable session API writes; preserve database audit; investigate tenant predicates | Session opaque IDs and sanitized audit metadata |
| Invalid webhook signature burst | Reject all invalid requests; do not decode or persist them | Provider account alias, timestamp, request digest and status |
| Outbox lease backlog | Pause provider dispatch; inspect stable error codes and lease age | Command IDs, error codes, attempts and timestamps |
| Unknown provider side-effect outcome | Do not blindly retry; reconcile provider state first | Internal command/session IDs and opaque provider resource IDs |
| Consent mismatch | Stop new recording joins; fail the session and cancel outstanding consent calls | Policy version, opaque participant refs and event digests |
| Media validation failure | Mark session DEGRADED; do not publish or serve the artifact | Format, size, channel count, validation code and digest |
| Deletion failure | Keep tombstone and retry; do not report deletion complete | Internal object/provider IDs, attempt count and error code |

## Rollback and recovery

- API rollback: ECS deployment circuit breaker is enabled; restore the previous image revision if readiness fails.
- Database restore: restore into an isolated instance first, verify tenant isolation and consent evidence, then authorize cutover.
- Outbox recovery: expired leases may be reclaimed, but every provider operation must reconcile before retry.
- Media deletion: retry Twilio and S3 deletion independently; do not erase the tombstone while either side remains.
- Disable new provider traffic by setting TWILIO_ENABLED=false and scaling worker/retention services to zero. This stops new session consent calls; it does not automatically terminate an already-running Conference. Use the provider adapter or Twilio Console for an incident stop and record the action.

## Remaining readiness gates

- Real Twilio account acceptance and actual recording/deletion.
- Physical iPhone/SIM carrier merge tests if claiming native SIM-call support.
- Counsel approval, paid-pilot evidence and selected launch market.
- Secret rotation procedure and alerts for outbox age/dead letters, webhook failures, unknown reconciliation, recording verification failures, retention backlog, API 5xx and spend.
- AWS resources have not been provisioned. Terraform is a reviewed source artifact, not a deployed staging environment.
