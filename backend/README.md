# Conference Bridge Backend Core

This is a provider-neutral domain and webhook-processing foundation, not a
deployable recording service and not a real PSTN provider integration.

## Included
- Typed bridge lifecycle and guarded transitions.
- Consent from every expected, joined participant before recording can start.
- Signature verification against original request bytes before event decoding.
- Atomic event-deduplication port; duplicate events are ignored.
- Fail-closed handling of invalid and out-of-order lifecycle events.
- Opaque participant references rather than phone numbers.

## Deliberate production gaps
The in-memory repository is a test fake only. Production requires a transactional
database with a unique (provider, event_id) constraint and atomic session updates.
No production signature verifier, provider adapter, HTTP endpoint, authentication,
secret store, media ingestion, audio verification, object storage, retention
worker or deletion integration is implemented.

Provider webhook adapters must use the exact signature algorithm, timestamp
tolerance and replay rules documented by the provider. This core does not invent
a generic HMAC scheme.

## Tests
From the repository root:
```sh
PYTHONPATH=backend python3 -m unittest discover -s backend/tests -v
```
No external packages or network access are required.
