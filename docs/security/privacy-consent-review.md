# Privacy and consent engineering review

**Review status:** engineering design review updated 2026-11-20. This is not jurisdiction-specific legal advice, a DPIA, App Store approval or evidence that any live capture flow is lawful.

## Product modes and data boundaries

| Mode | Data the app/backend handles | Recording source | Consent boundary |
|---|---|---|---|
| Native-call companion/import | User-selected audio file, opaque catalog ID, duration, size, import date | User obtains and exports the file through an OS-supported or external route | Importing does not prove the source recording was lawful or consented |
| Native SIM-call merge experiment | Opaque session refs and physical-device evidence | Existing SIM call plus carrier add-call/merge, if supported | Not validated; a merged PSTN leg may mix speakers and prevent reliable participant attribution |
| App-owned Twilio Conference | Opaque session/participant refs, consent evidence, provider IDs and recording | Two outbound Twilio participant calls and provider Conference | Every expected participant must independently consent before a recording-enabled Conference is created |
| App-owned VoIP | App-controlled call legs, consent evidence and provider media | App/provider media pipeline | Separate product mode; preflight disclosure and affirmative consent before recording-enabled joins |
| Accessory/acoustic | Imported artifact and exact accessory/device evidence | External hardware or independent recorder | Consent/indication must be handled by the actual capture workflow, not inferred from import |

These modes must remain distinct in product copy, API contracts and release claims. The implemented Twilio path is an app-owned outbound Conference; it is not native Phone.app audio interception or proof that an existing SIM call can be merged.

## Current data minimization controls

- iOS catalog stores only an opaque UUID, allowlisted container extension, byte count, duration and import timestamp. It does not persist original filename, phone number, contact name, transcript or call content.
- Imported media remains in app-private storage, is excluded from device backup and receives complete file protection. Export is user-initiated.
- Session API accepts bounded opaque participant references. Responses do not expose provider IDs or participant addresses.
- API bearer credentials are supplied as SHA-256 token digests mapped to tenant IDs; raw bearer tokens are not stored by the authenticator.
- PostgreSQL session reads, cancellation and participant-address provisioning are tenant-scoped.
- Participant addresses are encrypted with AES-256-GCM using tenant and participant reference as associated data. The database stores ciphertext only; the address API returns only a status. Provisioning/replacement/deletion produces a metadata-only audit record.
- Outbox payloads carry opaque participant references, not phone numbers, provider credentials or media URLs.
- Twilio webhook ingress verifies the exact configured HTTPS URL and original request body before decoding; event IDs and payload digests are persisted, not raw callback bodies.
- S3 media objects use tenant-derived opaque prefixes, UUID session/media IDs, server-side KMS encryption and short-lived presigned downloads. The caller must authorize the tenant before issuing a URL.
- Recording media is downloaded with RequestedChannels=2, structurally validated, and accepted only when both stereo PCM16 channels contain measurable activity. Only two-participant sessions are supported by this mapping.

## Consent invariants

1. The app never captures native Phone.app audio through private APIs or implies CallKit grants that access.
2. An imported audio file is not proof of two-party consent or legal provenance.
3. A participant join is forbidden until durable affirmative consent evidence exists for that exact opaque participant reference.
4. A recording-enabled app-owned Twilio Conference is created only after every expected participant has passed the pre-join DTMF consent gate.
5. Only DTMF 1 is affirmative. A non-affirmative entered digit is an explicit decline; empty Gather and busy/failed/no-answer/canceled outcomes are participant unavailability. Generic `CallStatus=completed` is informational, not a consent decision, because it can race with the authoritative Gather callback. All outcomes fail closed: no Conference is created without durable affirmative consent from every participant.
6. A decline or API cancellation dead-letters pending consent requests, prevents new consent dialing and queues cancellation of mapped outstanding consent calls.
7. A beep, initiator checkbox, webhook join event or a merged PSTN leg is not by itself proof that every human participant consented.
8. If participant identity, consent, signature, event ordering or provider state is uncertain, the operation fails closed or is held for reconciliation.
9. A session is marked COMPLETED only after a completed recording is retrieved, two-channel validation passes and encrypted object storage succeeds. Rejected media results in DEGRADED.
10. Media deletion is not complete until both the Twilio recording and S3 object have been deleted.

## Required legal/product decisions before launch

- Select one launch jurisdiction and define whether the user is acting as consumer, professional, employer or processor/controller.
- Obtain counsel review of recording law, notice timing, affirmative consent, cross-border transfer, data residency, employee monitoring, retention, deletion and evidentiary requirements.
- Define controller/processor roles and vendor DPAs for provider, cloud, object storage and support systems.
- Set a lawful basis and purpose limitation for each data category. Do not treat consent to record as consent to cloud storage, transcription, AI analysis or onward sharing.
- Define retention periods separately for local imports, provider-side recordings, object storage, consent evidence, audit events and backups.
- Provide user access/export/deletion and an operational process for deletion from provider copies, object versions, replicas and backups.
- Complete App Store privacy questionnaire and labels from the final app binary, manifests and actual SDK/network behavior.
- Ensure every capture flow presents a clear recording indication and meaningful unsupported/failure state.

## Release blockers

- No live Twilio account call, dual-channel recording or deletion has been verified.
- No physical native-SIM merge test or independent remote-party identity proof exists.
- No completed DPIA, legal opinion or launch-market approval.
- AWS Terraform and deployment workflow exist but no cloud environment, secret rotation or monitoring has been provisioned.
- No paid pilot, customer interviews, final App Store privacy-label submission or signed distribution build is complete.

**Decision:** current engineering controls are a privacy-by-design foundation, not a statement that the product is legally compliant or ready to record real calls. Keep TWILIO_ENABLED=false until all gates applicable to the selected product mode and launch jurisdiction are closed with evidence.
