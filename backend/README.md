# Conference Bridge Backend

This backend contains a provider-neutral session/outbox core, authenticated tenant-scoped ASGI API, live Twilio REST adapter and signed Twilio webhook/media pipeline. It has not been exercised against a live Twilio account and is not evidence of native SIM-call merge. The implemented Twilio path is an app-owned outbound two-party Conference: both participants receive provider calls after pre-join consent.

## Included

- Guarded bridge lifecycle and durable pre-join consent evidence.
- Tenant-scoped authenticated session create/read/cancel API.
- Transactional initial consent-request outbox commands.
- Twilio REST commands for outbound consent calls, Conference participant creation/addition, recording-from-start and Conference closure.
- DTMF Gather disclosure: only digit 1 is affirmative; empty input, other digits, busy, no-answer, failed and unconsented completed calls fail closed.
- Signed call-status, consent, Conference and Recording webhooks, with account-scoped resource ownership resolution.
- Separate immutable provider mappings for consent IVR call SIDs and Conference participant call SIDs.
- Encrypted tenant-scoped E.164 address vault with authenticated provisioning/deletion API and metadata-only audit trail.
- Supervised outbox worker and retryable media-retention worker.
- Twilio Conference recording retrieval with RequestedChannels=2, bounded WAV validation, stereo PCM16 activity checks, explicit channel ownership for two participants, KMS-backed S3 upload and coordinated Twilio/S3 deletion.

## Install and migrate

Install pinned dependencies:

```sh
python -m pip install -r backend/requirements.txt
```

Apply migrations in numeric order before starting services:

```sh
cd backend
python migrate.py
```

Migrations currently run through 0011_rejected_media_metadata.sql. The application does not run DDL at startup.

## API flow

1. Provision each participant address through authenticated PUT /v1/participants/{participant_ref}/address with a JSON phone_number field. The response never echoes the address.
2. Create a session with exactly two opaque participant_refs. When TWILIO_ENABLED=true, session creation and the two consent.request outbox commands commit atomically.
3. Both participants receive a separate consent call. Only after every affirmative Gather event does the reducer enqueue conference.create.
4. The first participant joins a recording-enabled Conference. Its join callback causes the second participant.add command.
5. Conference callbacks move the session into recording/finalization. A completed Recording callback triggers media retrieval and two-channel validation.
6. The session becomes COMPLETED only after both channels contain activity and encrypted object storage succeeds; otherwise it becomes DEGRADED. Retention deletes the Twilio recording and S3 object as separate retryable steps.

DELETE /v1/participants/{participant_ref}/address removes the tenant-scoped encrypted address and records a metadata-only audit event. GET /v1/bridge-sessions/{session_id}/media returns a 120-second presigned URL only for a verified, undeleted media asset and records the grant in media_access_audit. API session cancellation while consent calls may exist dead-letters pending consent requests and queues provider call cancellation.

## Runtime configuration

The ASGI factory is asgi:create_app. With TWILIO_ENABLED=false it exposes only the session API. Enabling Twilio requires all of the following to be injected from a secret manager:

- TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN.
- TWILIO_PROVIDER_ACCOUNT_ID and TWILIO_FROM_NUMBER.
- TWILIO_PUBLIC_ORIGIN (canonical public HTTPS origin).
- TWILIO_CONSENT_POLICY_VERSION and TWILIO_CONSENT_DISCLOSURE (exact counsel-approved text).
- PARTICIPANT_ADDRESS_KEY_HEX (32 random bytes encoded as 64 hex characters).
- MEDIA_BUCKET and MEDIA_KMS_KEY_ID.
- BRIDGE_API_TOKEN_HASHES and DATABASE_URL (or split DATABASE_HOST/PORT/NAME/USER/PASSWORD settings).

The standalone worker entry point is python worker_main.py. The retention service entry point is python retention_main.py. Compose exposes these only through its opt-in provider profile. Never use a personal production Twilio account for development.

## Live-account acceptance

The opt-in, staging-only real-account harness and its evidence/cleanup requirements are documented in [Twilio live-account acceptance](../docs/validation/twilio-live-account-acceptance.md). The executable is `backend/tools/twilio_live_acceptance.py`; it is inert without `--execute`, `BRIDGE_ENVIRONMENT=staging` and `TWILIO_LIVE_TEST_APPROVED=true`. Never run it in pull-request CI.

## Outbox and idempotency

The dispatcher commits a lease before provider I/O and reconciles every delivery before retrying. Consent calls and conference legs have distinct resource tables because their Call SIDs are different. Twilio Calls.create does not provide a general idempotency guarantee; if the provider side effect may have happened but no mapping was committed, the adapter returns UNKNOWN and does not dial again. This favors avoiding duplicate calls over automatic recovery.

A worker can crash after a provider side effect and before acknowledgement. Provider reconciliation remains mandatory; this is at-least-once command delivery, not exactly-once remote execution.

## Media channel semantics

Twilio dual-channel Conference recording places the first participant in channel 1 and all remaining participants in channel 2. The product therefore restricts this path to exactly two expected participants. The validator requires stereo PCM16 WAV and measurable activity in both channels. This verifies two active tracks and a provider-defined mapping; it is not voice biometrics and cannot prove that a specific human spoke.

The media endpoint explicitly requests RequestedChannels=2. Account-level dual-channel availability must be confirmed in the live Twilio account. A mono or silent-channel result is rejected and the session is DEGRADED rather than presented as a valid two-sided recording.

## Explicit boundaries

- No live Twilio account, PSTN call, recording, deletion or billable provider action was performed by CI.
- This app-owned outbound Conference is not native Phone.app audio capture and does not prove a user's existing SIM call can be merged.
- No AWS account or remote staging resources have been provisioned. Terraform and a manual OIDC deploy workflow are under infra/aws.
- No jurisdiction-specific legal approval, paid pilot, physical-device evidence, App Store approval or signed Release build is claimed.
