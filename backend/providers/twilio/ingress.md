# Twilio webhook ingress and event decoding

TwilioWebhookASGI is the bounded ASGI transport adapter for POST callbacks. It reconstructs the public URL from a configured canonical HTTPS origin plus the ASGI raw path/query, preserves the original body and parses form parameters once while retaining duplicate values. The same SignedWebhookRequest instance is passed to WebhookProcessor, which verifies the Twilio signature before invoking the configured event decoder.

## Mounted routes

When TWILIO_ENABLED=true, the production ASGI composition root mounts:

- /v1/twilio/consent — DTMF Gather result; after durable processing the route returns Hangup TwiML.
- /v1/twilio/call-status — busy/no-answer/failed/canceled outcomes mark the participant unavailable; generic completed status is informational and does not decide consent.
- /v1/twilio/conference — Conference start/end and participant join/leave callbacks.
- /v1/twilio/recording — recording in-progress/completed/failed/absent callbacks.

The decoder binds the callback to the configured Account SID before resolving provider resource IDs. Session and participant identity come only from immutable account-scoped database mappings; phone numbers and caller-supplied session IDs are not trusted. Consent IVR Call SIDs and Conference participant Call SIDs have separate persistence tables.

## Security requirements

- Configure the official Twilio verifier and canonical HTTPS origin.
- Do not trust arbitrary client-supplied X-Forwarded-Host or X-Forwarded-Proto headers.
- Use the exact external URL configured at Twilio, including query parameters and original encoding.
- Reject duplicate security-sensitive form fields.
- Never log full form payloads, caller numbers, signatures, Auth Tokens, provider SIDs or media URLs.
- Durable event-ID deduplication is enforced by the repository. Unknown provider-resource mappings fail closed.
- Public deployment must add ingress rate limits and monitoring; no rate-limit service is included in this ASGI adapter.

## Consent and media processing

The consent route only accepts digit 1 as affirmative. Empty Gather, other digits and terminal call outcomes without stored affirmative evidence fail the session. A decline queues cancellation of the other consent legs and pending consent requests are dead-lettered. The adapter does not generate a legal disclosure: the exact disclosure and policy version must be injected from a counsel-approved deployment secret.

Completed Conference recordings are retrieved with RequestedChannels=2, structurally validated, checked for stereo PCM16 and measurable activity on both channels, then stored with KMS encryption. A verified recording is mapped to two expected participant refs. Invalid or single-channel recordings are marked rejected and the session becomes DEGRADED. Twilio and S3 deletion are tracked as separate retryable steps.

## Limits

- The implemented Twilio flow calls two participants as separate outbound provider legs. It is not a native SIM-call merge or Phone.app audio capture path.
- No live Twilio account, PSTN call, recording, deletion, TLS endpoint or cloud deployment has been verified in CI.
- Dual-channel semantics and account availability must be confirmed in the live Twilio account.
- Physical iPhone/SIM tests remain mandatory for any native-SIM merge claim.
