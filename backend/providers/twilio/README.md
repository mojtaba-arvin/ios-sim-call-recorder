# Twilio webhook verifier

This adapter verifies inbound Twilio POST callbacks only. Configure the Twilio
Voice/Events webhook method as POST and use the exact public HTTPS URL configured
at Twilio, including query parameters and their original URL encoding.

## Supported request types

- `application/x-www-form-urlencoded`: the HTTP layer must parse all form
  parameters once, preserving duplicate/multi-value fields, and pass that same
  collection in `SignedWebhookRequest.form_parameters`. The event decoder must
  consume that same collection after verification.
- `application/json`: preserve the original request bytes and include the
  Twilio `bodySHA256` query parameter. The adapter verifies the original UTF-8
  body using the official SDK.

Unsupported content types, missing signatures, malformed bodies, missing JSON
body hashes and non-POST requests are rejected.

## Deployment requirements

- Load the Twilio Auth Token from a secret manager/environment injection; never
  put it in source control, app binaries, logs or webhook responses.
- Reconstruct the exact external URL using a configured canonical origin or
  trusted reverse-proxy metadata. Never trust arbitrary client-supplied
  `X-Forwarded-Host` or `X-Forwarded-Proto` values.
- Use HTTPS and the official Twilio Python SDK validator.
- Keep webhook handlers idempotent. Twilio retries deliveries; persist provider
  event IDs under a unique constraint.
- Do not log full form payloads, caller numbers, signatures, Auth Tokens or
  media URLs.

## Boundary

This verifier does not create conferences, dial participants, enable recording,
download media or prove that a carrier supports three-way merge. The current
implementation is a security adapter testable with synthetic requests only.

The request adapter must pass one `SignedWebhookRequest` instance to both the
signature verifier and the post-verification event decoder. For form callbacks,
the decoder must consume the same `form_parameters` collection used by the SDK
validator; it must not independently parse the raw body a second time.

The implementation uses the official SDK's default request-validation behavior.
If a Twilio account is configured for a non-default signature algorithm or a
different webhook mode, treat that as a compatibility change and add explicit
SDK-backed tests before enabling it; do not silently fall back to custom crypto.
