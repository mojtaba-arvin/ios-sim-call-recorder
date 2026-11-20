# Twilio webhook ingress

`TwilioWebhookASGI` is a bounded ASGI transport adapter for POST callbacks.
It reconstructs the public URL from a configured canonical HTTPS origin plus
the ASGI raw path/query, preserves the original body, and parses form
parameters once while retaining duplicate values. The same
`SignedWebhookRequest` instance is passed to `WebhookProcessor`, which
verifies the provider signature before invoking the injected event decoder.

The event decoder is deliberately injected: this transport component does not
guess Twilio callback semantics or synthesize event identities. A production
decoder must bind provider account, session and participant resources using
persisted mappings; it must not trust phone numbers or client-provided session
IDs. Configure the official Twilio verifier and canonical origin, and reject
non-default provider signature modes until SDK-backed tests cover them.

The ingress is not yet mounted in a deployed server. Authentication, replay
policy beyond durable event-ID deduplication, provider account preflight,
production decoder, TLS ingress, rate limiting and operational monitoring
remain deployment gates.
