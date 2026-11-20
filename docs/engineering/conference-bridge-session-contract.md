# Conference Bridge Session Contract

> Status: provider-neutral contract. Authenticated tenant-scoped session API components now exist; live provider execution, consent IVR and carrier merge remain unimplemented.
> Reviewed: 2026-11-20
> Related work: [P02 proof issue](https://github.com/mojtaba-arvin/ios-sim-call-recorder/issues/2)

## 1. Operating boundary

The iOS app does not receive the native cellular call's live audio and does not silently control the Phone app's merge UI. The user performs the carrier call and add/merge actions using the system Phone interface. The app coordinates a bridge session, displays instructions and observes provider events.

The bridge records only after every required participant has received a clear disclosure and affirmatively consented. Consent evidence is part of the session audit record. A provider announcement alone is not assumed to satisfy every jurisdiction's consent requirement.

## 2. User and backend flow

1. App requests a new bridge session with an explicit call direction and target region.
2. Backend creates a session in `created`, assigns an opaque short-lived join token and selects an eligible provider route.
3. App displays the exact manual steps: call the intended party, add the bridge destination, then merge. The UI explains that carrier support is required.
4. Provider receives the bridge leg and emits signed call/conference webhooks.
5. Bridge plays a recording disclosure separately to each participant and collects affirmative consent (for example, a DTMF confirmation) before recording is enabled.
6. Backend verifies all required participants have consented, then enables recording.
7. Provider emits recording lifecycle events. Backend retrieves media using server-side credentials, validates integrity and stores it in encrypted product storage.
8. Audio verification checks both directions, duration, clipping, gaps and channel mapping. The session is `completed` only if the declared acceptance criteria pass; otherwise it remains `degraded` or `failed`.
9. Retention and deletion policies apply to both provider-side and product-side copies.

## 3. Session states

| State | Meaning |
|---|---|
| created | Session and opaque join token created |
| awaiting_user_action | User must place/answer the carrier call and manually merge |
| bridge_leg_ringing | Provider is dialing or waiting for the bridge participant |
| participants_joining | Bridge has one or more participant legs |
| awaiting_consent | Required participants have not all consented |
| recording | Consent gate passed and provider recording is active |
| finalizing | Call ended; recording/media finalization is pending |
| verifying | Media is downloaded and checked |
| completed | Required audio and integrity checks passed |
| degraded | Media exists but one or more declared quality/coverage checks failed |
| failed | Setup, consent, provider, media or validation failure |
| cancelled | User or system cancelled before completion |

Only explicit, idempotent transitions are accepted. Provider events may arrive late or out of order; event timestamps alone must not override a newer terminal state.

## 4. Provider-neutral API contract

### Create session

`POST /v1/bridge-sessions`

Request fields:
- `client_request_id`: client-generated idempotency key
- `call_direction`: `incoming` or `outgoing`
- `country_code`: intended physical test country
- `locale`: user-facing instruction and disclosure locale
- `participant_count`: expected number of human participants
- `consent_policy_version`: version of the disclosure/consent policy

Response fields:
- `session_id`
- `state`
- `join_destination`: provider bridge number or approved URI
- `expires_at`
- `manual_instructions`
- `capability_decision_id`

The response must not expose provider credentials, raw provider identifiers or long-lived join secrets.

### Read session

`GET /v1/bridge-sessions/{session_id}`

Returns state, sanitized participant status, consent status, expiry, failure code and recording verification summary. It never returns recording media through this endpoint.

### Cancel session

`POST /v1/bridge-sessions/{session_id}/cancel`

Idempotent. A cancellation after recording begins must stop/close the provider conference and finalize or delete any partial media according to policy.

## 5. Webhook contract

Provider adapters normalize events into:
- `provider_event_id`
- `provider_session_id`
- `provider_call_id`
- `event_type`
- `occurred_at`
- `received_at`
- `participant_ref` (opaque, never raw phone number in ordinary logs)
- `payload_digest`

Requirements:
- Verify provider signatures against the raw request body and documented timestamp rules.
- Reject invalid signatures and stale/replayed requests.
- Deduplicate by provider event ID with a unique database constraint.
- Persist the raw encrypted event only when needed for audit/debugging; redact or tokenize phone numbers.
- Acknowledge quickly after durable enqueue; process state changes asynchronously.
- Never trust a webhook media URL without validating provider ownership and fetching it with server-side credentials.
- Make every handler idempotent and safe under duplicate delivery and out-of-order arrival.

## 6. Data and security requirements

- Separate tenant/session authorization from provider credentials.
- Store provider secrets in a managed secret store; never in the app or repository.
- Encrypt media in transit and at rest with tenant-scoped access control.
- Use opaque participant references; avoid caller ID as the sole identity or consent proof.
- Keep a tamper-evident audit trail for disclosure, affirmative consent, recording start/stop, media retrieval, access, export and deletion.
- Define retention and deletion for provider and product copies before launch.
- Do not log audio, access tokens, full phone numbers or signed media URLs.
- Exclude emergency calls and any flow where consent or participant identity cannot be safely established.

## 7. Audio verification contract

A media artifact is not automatically a successful recording. Verification must record:
- duration and expected/observed participant count
- local and remote speech intelligibility independently
- channel layout and channel-to-participant mapping
- clipping, silence gaps, packet loss artifacts and synchronization
- sample rate, bit depth, codec and container
- provider recording status and media checksum

For a two-party call, synthetic phrase sets must establish which channel contains each side. For conferences with more than two participants, record whether other participants are mixed together. Never promise isolated per-person tracks unless proven.

## 8. Failure taxonomy

- `carrier_conference_unsupported`
- `user_merge_failed`
- `bridge_timeout`
- `participant_declined_consent`
- `consent_missing`
- `provider_webhook_invalid`
- `provider_event_conflict`
- `recording_not_created`
- `media_download_failed`
- `audio_local_missing`
- `audio_remote_missing`
- `audio_quality_below_threshold`
- `retention_delete_failed`

Failures must be visible to the user in plain language and persisted with the exact compatibility tuple. Never silently mark a partial recording as complete.

## 9. Non-goals

- Intercepting or recording native Phone audio directly from the iOS app.
- Automatically merging cellular calls through undocumented APIs.
- Treating call forwarding as proof of two-way recording.
- Claiming universal support across carriers, regions or iPhone models.
