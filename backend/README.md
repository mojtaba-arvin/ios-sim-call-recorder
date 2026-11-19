# Conference Bridge Backend Core

This is a provider-neutral domain and webhook-processing foundation, not a
deployable recording service and not a real PSTN provider integration.

## Included
- Typed bridge lifecycle and guarded transitions.
- Consent from every expected, joined participant before recording can start.
- Provider-native signature verification using the exact request URL, method,
  content type, headers, original body and (where required) syntactically parsed
  form parameters before business event decoding.
- Atomic event-deduplication port; duplicate events are ignored.
- Fail-closed handling of invalid and out-of-order lifecycle events.
- Opaque participant references rather than phone numbers.

## Deliberate production gaps
The in-memory repository is a test fake only. Production requires a transactional
database with a unique (provider, event_id) constraint and atomic session updates.
No production signature verifier, provider adapter, HTTP endpoint, authentication,
secret store, media ingestion, audio verification, object storage, retention
worker or deletion integration is implemented.

The webhook processor passes the same verified request object to the business
decoder. This is important for form callbacks: signature validation and event
normalization must consume the same parsed parameter collection, not parse the
raw form body independently with potentially different duplicate/encoding rules.

Provider webhook adapters must use the exact signature algorithm and request
semantics documented by that provider's official SDK. For example, Twilio's
form-encoded and JSON webhook validation inputs differ; never replace its SDK
validator with a generic raw-body HMAC implementation. The public URL used for
validation must be reconstructed from trusted deployment/proxy configuration,
not arbitrary client-supplied forwarding headers.

## Tests
From the repository root:
```sh
PYTHONPATH=backend python3 -m unittest discover -s backend/tests -v
```
No external packages or network access are required.
