# Twilio webhook event decoder

`TwilioWebhookEventDecoder` is the account-bound normalization layer used after
`WebhookProcessor` has validated the Twilio request signature. It supports
three explicit callback paths:

- `/consent`: accepts only an affirmative `Digits=1` Gather callback and emits
  durable pre-join consent evidence using the configured policy version.
- `/conference`: maps Conference start, participant join and Conference end
  callbacks to provider-neutral domain events.
- `/recording`: maps completed/failed Recording callbacks to lifecycle events.

## Required integration contract

The decoder is intentionally not a TwiML generator or provider command adapter.
The application must:

1. Mount the three routes behind `TwilioWebhookASGI` and use the same canonical
   HTTPS origin used to configure Twilio's webhook URLs.
2. Run `WebhookProcessor` so signature verification happens before this decoder.
3. Configure the expected Account SID and an opaque internal provider-account ID.
4. Supply `resolve_session(call_sid, conference_sid)` backed by immutable,
   account-scoped provider resource mappings. It must reject unknown or ambiguous
   resources and return only an internal session ID and opaque participant ref.
5. Configure a consent policy version that identifies the exact disclosure text
   and legal review revision used by the TwiML/Gather flow.

Twilio SIDs, phone numbers and Recording URLs are used only transiently to resolve
ownership. They are not copied into `NormalizedProviderEvent`; only a SHA-256
payload digest and a derived event identity are persisted. The decoder does not
claim that a consent Gather prompt exists until the application deploys the
corresponding reviewed TwiML and consent route.

The decoder uses Twilio's `I-Twilio-Idempotency-Token` when present. Otherwise,
it derives a stable delivery identity from the callback route, resource identity
and raw payload digest. The event timestamp uses Twilio's RFC-2822 `Timestamp`
when supplied; otherwise it uses the injected receipt clock.

## Tests

Run:

```sh
PYTHONPATH=backend python -m unittest backend.tests.test_twilio_events -v
```

No live Twilio credentials or paid calls are required.
