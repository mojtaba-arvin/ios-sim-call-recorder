# Twilio live-account acceptance harness

**Status:** harness implementation; no live account call has been run.  
**Purpose:** execute an explicitly approved two-party outbound Conference acceptance test against a staging API. This is not a native SIM-call merge test.

## Safety contract

The harness is inert by default. It places real PSTN calls only when all of the following are true:

- Invoke with `--execute`.
- `BRIDGE_ENVIRONMENT=staging`.
- `TWILIO_LIVE_TEST_APPROVED=true`.
- `BRIDGE_BASE_URL` is an HTTPS staging endpoint.
- `BRIDGE_API_TOKEN` is a staging-only bearer token.
- `TWILIO_TEST_PARTICIPANT_A` and `TWILIO_TEST_PARTICIPANT_B` are distinct, authorized E.164 test numbers.
- Both participants have received the test notice and explicitly agree to the test.
- Counsel-approved disclosure and policy version are configured on the staging service.
- Twilio account spending alerts and a bounded test budget are active.

Never use production participant numbers, personal production Twilio accounts, real conversations, or secrets in command-line arguments. Do not enable live Twilio in CI. Keep the token and phone numbers in the operator's protected environment, not GitHub logs or artifacts.

## Install and dry-run

From the repository root:

```sh
python backend/tools/twilio_live_acceptance.py
```

This performs no network requests and no calls.

## Positive acceptance run

Set the required environment variables in a protected local shell or approved secret-injection environment, then run:

```sh
python backend/tools/twilio_live_acceptance.py --execute --expect-state completed
```

The harness provisions two opaque participant refs, creates one session, waits for the two consent legs and Conference flow, retrieves only the API's verified media asset, downloads it to a temporary file, runs the repository's dual-channel WAV analyzer, deletes the temporary file, and prints a sanitized evidence summary. It never prints phone numbers, bearer tokens, Twilio Auth Tokens, signed media URLs or webhook payloads.

A completed result is acceptable only when both participants are recorded as consented, the session reaches `completed`, and the downloaded recording passes stereo PCM16/two-channel activity analysis.

## Negative acceptance runs

Run separately for explicit DTMF decline and no-answer/busy cases, coordinating the action with the two test participants. The API distinguishes an explicit non-affirmative digit (`participant_declined_consent`) from no response or a terminal call outcome (`participant_unavailable`). A generic `completed` call-status callback is not treated as refusal because it can race with the authoritative Gather callback:

```sh
python backend/tools/twilio_live_acceptance.py --execute --expect-state failed
```

The operator must record which participant declined or did not answer in a private test record. The public harness output contains only the backend failure code. A failed/declined session must never return a verified media download.

## Required evidence and cleanup

For every run, retain privately:

- UTC start/end timestamps and harness version/commit SHA.
- Session ID and terminal state.
- Sanitized counts for expected, consented and joined participants.
- Twilio Call/Conference/Recording SIDs in the restricted provider evidence store only (never public CI artifacts).
- Signed callback verification outcome and callback ordering.
- Media SHA-256, byte count, duration, sample rate, stereo channel activity and secure artifact reference.
- Confirmation of Twilio recording deletion and S3 object deletion after retention processing.

The harness reports retention cleanup as pending. The operator must verify both deletion paths independently; a successful media download is not proof of deletion. Delete test participant addresses through the authenticated API after the run and verify the metadata-only audit event. Preserve only sanitized evidence under the approved retention schedule.

## Limits

- This tests the app-owned outbound Twilio Conference path, not the user's existing native SIM call or Phone.app audio.
- It does not certify a carrier, iPhone model, iOS build, Bluetooth route or native call merge.
- It cannot replace jurisdiction-specific legal approval or a physical-device test.
- Do not mark Twilio acceptance passed until a real run's sanitized output and private provider/deletion evidence have been reviewed.
