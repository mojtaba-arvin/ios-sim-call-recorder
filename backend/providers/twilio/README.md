# Twilio Voice adapter

This package implements a Twilio Programmable Voice outbound Conference flow and signed webhook processing. It is not native SIM-call audio capture. The service calls both participants as separate outbound PSTN legs after explicit DTMF consent.

## Runtime path

1. The authenticated API provisions E.164 addresses into the tenant-scoped AES-GCM address vault. Writes/deletes create metadata-only audit rows.
2. Session creation enqueues one consent.request command per expected participant in the same PostgreSQL transaction.
3. The outbox worker uses the Twilio REST API to call each participant and plays the configured disclosure with a one-digit Gather. Only DTMF 1 is affirmative.
4. Empty Gather, other digits, busy, failed, no-answer or an unconsented completed call marks the session failed and queues cancellation of the other consent legs.
5. After all participants consent, the reducer enqueues a recording-enabled Conference participant creation. The first participant join event causes the second participant.add command.
6. Signed Conference callbacks map provider resource IDs to the immutable account/session/participant records. Consent IVR call SIDs and Conference participant call SIDs are stored separately.
7. Recording callbacks trigger media retrieval, two-channel verification, encrypted object storage and session finalization.

## Required environment

- TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN.
- TWILIO_PROVIDER_ACCOUNT_ID (opaque internal account alias).
- TWILIO_FROM_NUMBER (verified E.164 Twilio caller ID).
- TWILIO_PUBLIC_ORIGIN (canonical public HTTPS origin, no trailing slash).
- TWILIO_CONSENT_POLICY_VERSION and TWILIO_CONSENT_DISCLOSURE (exact counsel-approved disclosure).
- PARTICIPANT_ADDRESS_KEY_HEX (32-byte AES key, 64 hexadecimal characters).
- MEDIA_BUCKET and MEDIA_KMS_KEY_ID.
- DATABASE_URL or split DATABASE_HOST, DATABASE_PORT, DATABASE_NAME, DATABASE_USER and DATABASE_PASSWORD.

Use an API Key/Secret pair if the deployment has one; otherwise the SDK client falls back to Account SID/Auth Token. The Auth Token is still required for webhook signature validation.

## Webhook routes

All callbacks are POST form-encoded and pass through the official Twilio signature validator before decoding:

- /v1/twilio/consent — Gather result; returns Hangup TwiML after durable processing.
- /v1/twilio/call-status — terminal consent-call status; completed without persisted consent fails closed.
- /v1/twilio/conference — Conference start/end and participant join/leave callbacks.
- /v1/twilio/recording — recording in-progress/completed/failed/absent lifecycle callbacks.

Configure these exact HTTPS URLs in the Twilio call/Conference settings. The canonical public origin is configured server-side; arbitrary forwarded headers are not trusted. Never log form payloads, caller numbers, signatures, provider SIDs or media URLs.

## Recording and channel mapping

Conference creation requests recording-from-start and dual channels. Media retrieval requests RequestedChannels=2. Twilio documents channel 1 as the first participant and channel 2 as all remaining participants. The current product path permits exactly two expected participants so the second channel represents the other party rather than a group mix.

The validator accepts bounded stereo PCM16 WAV only and requires audible activity in both channels. This is an audio-presence check, not speaker recognition. Mono, malformed, oversized or silent-channel media is rejected; the session is marked DEGRADED rather than claiming two-sided success.

## Retry and reconciliation

Twilio Calls.create has no general idempotency guarantee. If a create request may have succeeded but the Call SID was not persisted, the adapter returns UNKNOWN and does not place a duplicate call. Conference participant reconciliation uses the stable Conference friendly name and opaque participant label. Uncertain outcomes are never blindly replayed.

On participant decline or API cancellation, pending consent requests are dead-lettered, terminal session state prevents further dialing, and mapped outstanding consent legs are completed. Provider closure is reconciled before acknowledgement.

## Local tests

```sh
PYTHONPATH=backend python -m unittest backend.tests.test_twilio_events backend.tests.test_twilio_adapter backend.tests.test_twilio_ingress backend.tests.test_twilio_media -v
```

These tests use deterministic fake SDK resources and synthetic WAV fixtures. They do not create live Twilio calls.

## Live enablement gates

- Counsel-approved disclosure and launch jurisdiction.
- A dedicated Twilio subaccount, verified caller ID and approved outbound destinations.
- Public HTTPS webhook endpoint and account-level dual-channel recording availability.
- Authorized test participants and budget alerts.
- A real test proving consent callbacks, Conference join ordering, RequestedChannels=2 retrieval, independent audio in both channels and deletion from Twilio plus S3.
- Physical iPhone/SIM tests if the product claim includes merging an existing native SIM call. The Twilio outbound Conference alone does not prove that claim.
