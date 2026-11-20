# Counsel-ready legal and privacy brief

**Status:** engineering preparation only. This is not legal advice, a legal opinion, a DPIA, or App Store approval.  
**Blocking input:** the product owner has not selected a launch jurisdiction, customer segment or operating role.

## Product mode under review

The proposed carrier-bridge mode calls each expected participant for explicit DTMF consent, then creates a two-party Twilio Conference and records from conference start. The service retrieves the recording, validates two active WAV channels, stores it encrypted in an S3 bucket, and deletes the provider copy and object after the configured retention period.

This is not native Phone.app audio interception. The companion/import mode and app-owned VoIP mode must be reviewed separately.

## Data flow for counsel

1. Authenticated tenant submits two opaque participant references.
2. Tenant provisions E.164 addresses through the authenticated API; the backend encrypts them with AES-256-GCM and writes a metadata-only audit record.
3. Backend calls each participant and plays the configured disclosure.
4. Only affirmative DTMF "1" produces consent evidence. Any other key, empty Gather result, busy, failed, no-answer or completed call without recorded consent fails the session and queues cancellation of outstanding consent legs.
5. Only after every expected participant has consented does the outbox create a recording-enabled Conference.
6. Twilio sends signed Conference and Recording callbacks. The backend resolves provider IDs through account-scoped mappings.
7. The completed media is downloaded with RequestedChannels=2, structurally validated, checked for active audio in both channels, encrypted with KMS and stored under opaque tenant/session/media IDs.
8. The database records channel ownership, digest, verification state and retention deadline.
9. Retention worker deletes the Twilio recording and S3 object as two independently retried steps; deletion is not complete until both are confirmed.

## Questions requiring a jurisdiction-specific answer

- Is recording lawful for each participant's location, and what exact notice/affirmative-consent standard applies?
- Is consent to recording sufficient, or is separate consent required for cloud storage, transcription, AI processing, export or cross-border transfer?
- What happens when a participant withdraws consent after the recording begins?
- Are there sector-specific rules (health, legal, financial, employment, education or regulated communications)?
- Does placing an outbound provider call to bridge an existing SIM call change the applicable telecom, caller-ID, number-use or call-forwarding rules?
- What controller/processor roles apply to the customer, app operator, Twilio and AWS?
- What DPAs, international transfer mechanisms, residency controls and subprocessor disclosures are required?
- What retention period is proportionate, and how must backups, provider copies and object versions be deleted?
- What user access, export, correction and deletion rights apply?
- What App Store privacy disclosures, permission prompts and recording indicators are required for each product mode?

## Required counsel deliverables

- Written approval or rejection for one named jurisdiction and product mode.
- Approved disclosure text and consent policy version.
- Approved data-flow diagram, lawful basis, retention schedule and deletion policy.
- Vendor DPA/subprocessor and transfer review.
- Review of terms, privacy notice, support process and App Store privacy labels.
- Explicit constraints on product marketing and supported use cases.

## Safe interim alternative

Until counsel signs off, keep TWILIO_ENABLED=false, do not place real calls, and limit the product to the companion/import workflow using user-provided files. The import UI must not imply that it creates a recording or proves the source recording was lawful.
