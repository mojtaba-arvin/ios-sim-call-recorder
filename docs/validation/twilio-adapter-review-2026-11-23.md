# Twilio Adapter Static Review — 2026-11-23

**Review scope:** `backend/providers/twilio/adapter.py`, `backend/bridge_core/dispatcher.py`, `backend/bridge_core/worker.py`, `backend/worker_main.py`, adapter tests, provider README, Issue #16 and ADR-0002.  
**Review tier:** static source/test review. No Twilio credentials, live requests, PSTN calls, account configuration or recording deletion were exercised.

## Executive result

The mainline implementation contains a concrete Twilio Programmable Voice adapter, consent IVR, recording-from-start Conference participant creation, signed callback processing, provider resource reconciliation, dual-channel media verification and coordinated retention deletion. The static design preserves the key boundary: this is an app-owned outbound Conference flow, not native SIM-call audio capture.

No source-level reason was found to claim a live provider acceptance pass. Issue #16 remains open for external acceptance.

## Positive controls observed

1. **Pre-join consent:** the dispatcher rejects `conference.create` unless `recording_mode == from_start`; the adapter enforces the same invariant before the provider call. The domain flow collects affirmative consent for every expected participant before enqueuing the recording-enabled conference join.
2. **Opaque participant identity:** adapter resolves an opaque participant reference to E.164 only at the provider side-effect boundary; malformed refs and addresses are rejected.
3. **Account/resource boundaries:** Account SID and returned Call/Conference SID shapes are checked; provider mappings are scoped by provider account and session; consent-call SIDs are stored separately from Conference participant Call SIDs.
4. **No blind replay:** dispatcher reconciles before executing. The adapter returns UNKNOWN after ambiguous later attempts when a resource cannot be proven; the dispatcher defers instead of acknowledging or blindly retrying.
5. **Provider timeout:** the production worker constructs the Twilio SDK client with `http_timeout=10`. Provider 429/5xx are retryable; ordinary 4xx responses are treated as non-retryable. Error text is sanitized before persistence/logging.
6. **Recording semantics:** Conference joins request `record-from-start` and dual-channel mode. Media retrieval separately requests two channels and validates actual WAV channel activity; the provider README correctly warns that channel 2 represents all participants other than the first, not speaker diarization.
7. **Privacy:** provider credentials remain server-side; phone addresses are resolved from the encrypted vault; callback payloads, signed URLs and audio are not intended for ordinary logs/outbox records.

## Findings / follow-up

| ID | Severity | Finding | Required action |
|---|---|---|---|
| C1-01 | External blocker | No real Twilio staging account acceptance is evidenced. Fake SDK resources cannot validate account settings, callback order, carrier behavior, actual media retrieval or deletion. | Run the opt-in harness only after authorized account, two consenting test numbers, approved disclosure, spending cap and staging deployment are available. |
| C1-02 | External blocker | Account-level dual-channel recording and actual channel semantics are not proven by local tests. | Confirm account preflight, download actual WAV, inspect both channels independently, then verify provider and S3 deletion separately. |
| C1-03 | P2 | `TwilioConferenceCommandAdapter.request_timeout_seconds` is validated and stored but not used to configure the SDK client. The current production entry point independently configures `Client(..., http_timeout=10)`; the adapter parameter therefore is not an effective runtime control. | Remove the unused parameter or make the timeout contract explicit in a follow-up code PR. Do not rely on it as a timeout setting. |
| C1-04 | External blocker | Reconciliation by stable Conference friendly name and opaque participant label is covered with fakes, but its behavior against the selected Twilio account/API configuration is unverified. | Verify create-timeout-after-acceptance and participant lookup against staging, without introducing duplicate PSTN side effects. |
| C1-05 | External blocker | Consent disclosure text and jurisdiction are configuration inputs, not legal approval. | Obtain written counsel approval of exact wording, jurisdiction, retention and deletion flow before enabling live Twilio. |

## Retry / idempotency review

- Twilio `Calls.create` is not treated as idempotent. On the first attempt the adapter may execute; after an ambiguous retry without a persisted Call SID it returns UNKNOWN rather than dialing again.
- Conference creation uses a stable session-derived friendly name and participant label for reconciliation. Multiple matching active Conferences or ambiguous participant lookup fail closed.
- Resource mappings are persisted before outbox acknowledgement.
- Database idempotency protects session creation and the initial outbox write; it does not guarantee exactly-once remote provider execution.
- The worker uses a 60-second lease and the runtime currently defaults to a batch of 10 commands. Because provider reconciliation and execution are sequential network operations, see the separate outbox-worker reliability follow-up; do not increase batch size without a lease-duration bound or renewal.

## Required live acceptance sequence

1. Dedicated staging subaccount and verified caller ID; approved outbound test destinations.
2. Two distinct consenting test participants; exact disclosure and policy version approved.
3. Verify consent success, explicit decline, no-answer/busy, cancellation race and callback replay.
4. Verify Conference creation occurs only after both consents; first recording-enabled participant is configured for record-from-start.
5. Verify actual Conference callbacks and resource mapping against the configured account.
6. Retrieve media with RequestedChannels=2; inspect both channels for the synthetic local/remote phrase set, duration, clipping, gaps and truncation.
7. Verify deletion independently at Twilio and S3; confirm metadata-only audit evidence.
8. Retain sanitized evidence with exact commit SHA and private provider IDs only in the restricted evidence store.

## Release boundary

- This review is not a live Twilio acceptance test.
- This review does not establish native SIM-call merge, Phone.app audio access, carrier support or physical iPhone compatibility.
- Do not enable `TWILIO_ENABLED` until live provider, physical pathway and legal gates are separately approved.
