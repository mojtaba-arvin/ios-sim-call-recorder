# Recording session lifecycle and cancellation

**Scope:** reusable Swift core orchestration contract. This document describes application-owned adapter sessions; it does not grant access to native Phone.app audio.

## State lifecycle

```text
idle -> preparing -> awaitingConsent -> connecting -> recording
                                    ^         |         |
                                    |         v         v
                                    |      cancelling  interrupted
                                    |         |         |
                                    |         v         +--> connecting
                                    |      cancelled
                                    |
recording / interrupted -> finalizing -> completed | degraded
Any active operation may fail -> failed
```

The state machine is authoritative. A terminal state cannot be reopened; create a new orchestrator instance for each recording session.

## Consent gate

1. `prepare` reserves one session ID before awaiting capability discovery.
2. The adapter prepares pathway resources and the state becomes `awaitingConsent`.
3. `startRecording` reserves `connecting` before awaiting the trusted consent verifier.
4. Structurally incomplete evidence or a negative verifier result fails closed.
5. Only after the verifier accepts the authoritative evidence may the adapter connect and start capture.
6. A completed artifact is accepted only when metadata is structurally valid and both local and remote audio are independently verified. Otherwise the result is `degraded`.

The core's structural checks do not establish consent authenticity. The injected verifier must check the evidence reference, policy version, participant coverage and authoritative audit persistence.

## Cancellation contract

- A session can be cancelled after `prepare` returns, while awaiting consent, connecting, recording or interrupted.
- The current preparation phase itself is not cancellable. Callers must wait for `prepare` to return before requesting cancellation.
- Cancellation first reserves the `cancelling` state, preventing a concurrent `finish` or new `startRecording` from winning the race.
- The adapter's `cancel(sessionID:)` must be idempotent, release partial resources and coordinate with in-flight connect/start calls. A late adapter completion must not restart capture after cancellation.
- The orchestrator checks session ownership and state after each asynchronous verifier/connect/start boundary. A continuation that resumes after cancellation returns `sessionCancelled` and cannot transition back to `recording`.
- If adapter cancellation fails, the orchestrator enters `failed`; callers must treat resource cleanup as uncertain and reconcile the adapter/provider before retrying.
- A cancellation request is rejected after finalization has started. Finalization and cancellation are mutually exclusive terminal paths.

## Actor reentrancy invariants

The actor serializes synchronous state transitions, but every `await` is a reentrancy boundary. Therefore:

- Reserve the next state before the first suspension point.
- Re-check active session identity and expected state after every awaited external operation.
- Never assume actor isolation prevents another actor call from running while the current method is suspended.
- Keep provider I/O outside database transactions; use the backend outbox/reconciliation flow for remote effects.
- Do not retry an uncertain create/connect/start operation without first reconciling remote state.

## Adapter implementation requirements

Every concrete adapter must define:

- capability decisions scoped to the complete compatibility context
- prepare/connect/start/finish semantics and cleanup ownership
- idempotent cancellation behavior for partial and active sessions
- timeout and unknown-outcome behavior
- consent and recording-notice integration
- artifact metadata and independent local/remote audio verification
- redacted diagnostics without phone numbers, raw audio, tokens or signed recording URLs

A mock adapter passing core tests does not certify a carrier, provider, accessory or physical device.
