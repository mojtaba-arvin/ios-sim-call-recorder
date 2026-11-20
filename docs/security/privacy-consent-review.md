# Privacy and consent engineering review

**Review status:** engineering design review completed 2026-11-20. This is not jurisdiction-specific legal advice, a DPIA, App Store approval or evidence that any live capture flow is lawful.

## Product modes and data boundaries

| Mode | Data the app/backend handles | Recording source | Consent boundary |
|---|---|---|---|
| Native-call companion/import | User-selected audio file, opaque catalog ID, duration, size, import date | User obtains and exports the file through an OS-supported or external route | The app must not imply that importing proves the source recording was lawful or consented |
| Carrier conference bridge | Opaque session/participant refs, signed consent evidence, provider resource IDs, later media | Carrier conference merge plus provider media | Every human participant must be independently identified and affirmatively consent before the first recording-enabled join |
| App-owned VoIP | App-controlled call legs, consent evidence, provider media | App/provider media pipeline | Preflight disclosure and affirmative consent before recording-enabled joins |
| Accessory/acoustic | Imported artifact and exact accessory/device evidence | External hardware or independent recorder | Clear indication and consent must be handled by the actual capture workflow, not inferred from the companion import UI |

These modes must remain distinct in product copy, API contracts and release claims.

## Current data minimization controls

- iOS catalog stores only an opaque UUID, allowlisted container extension, byte count, duration and import timestamp. It does not persist the original filename, phone number, contact name, transcript or call content.
- Imported media remains in app-private storage, is excluded from device backup and receives complete file protection. Export is user-initiated.
- Session API accepts only bounded opaque participant references. Responses do not echo them or expose provider IDs.
- API bearer credentials are supplied as SHA-256 token digests mapped to tenant IDs; raw bearer tokens are not stored by the authenticator.
- PostgreSQL session reads and cancellation are tenant-scoped.
- Participant addresses are encrypted with AES-256-GCM using tenant and participant reference as associated data. The database stores ciphertext only; plaintext is returned only to a trusted server-side caller.
- Outbox validation rejects common phone/address/credential/media fields. Webhook transport preserves raw bytes for signature verification and does not log payloads.
- S3 media objects use tenant-derived opaque prefixes, UUID session/media IDs, server-side KMS encryption and short-lived (60–300 second) presigned download URLs. The calling service must authorize the tenant before issuing a URL.

## Consent invariants

1. The app never captures native Phone.app audio through private APIs or implies CallKit grants that access.
2. An imported audio file is not proof of two-party consent or legal provenance.
3. A participant join is forbidden until durable affirmative consent evidence exists for that exact opaque participant reference.
4. A recording-enabled Twilio conference is created only after every expected participant has passed the pre-join consent gate.
5. A beep, initiator checkbox, webhook join event, or a merged PSTN leg is not by itself proof that every human participant consented.
6. If participant identity, consent, signature, event ordering or provider state is uncertain, the operation fails closed or is held for reconciliation.
7. A cancellation endpoint never claims to stop a provider call unless a provider close operation is confirmed.

## Required legal/product decisions before launch

- Select one launch jurisdiction and define whether the user is acting as consumer, professional, employer or processor/controller.
- Obtain counsel review of recording law, notice timing, affirmative consent, cross-border transfer, data residency, employee monitoring, retention, deletion and evidentiary requirements.
- Define controller/processor roles and vendor DPAs for provider, cloud, object storage and support systems.
- Set a lawful basis and purpose limitation for each data category. Do not treat consent to record as consent to cloud storage, transcription, AI analysis or onward sharing.
- Define retention periods separately for local imports, provider-side recordings, object storage, consent evidence, audit events and backups.
- Provide user access/export/deletion and an operational process for deletion from provider copies, object versions, replicas and backups.
- Complete the App Store privacy questionnaire and labels from the final app binary, manifests and actual SDK/network behavior.
- Ensure every capture flow presents a clear recording indication and a meaningful unsupported/failure state.

## Release blockers

- No live carrier-merge consent topology or independent remote-party identity proof.
- No production consent IVR or provider command adapter.
- No completed DPIA, legal opinion or launch-market approval.
- No deployed cloud service, managed secrets/rotation, object-store bucket policy, retention worker or deletion reconciliation.
- No final App Store privacy-label submission or signed distribution build.

**Decision:** current engineering controls are a foundation for privacy-by-design, not a statement that the product is legally compliant or ready to record real calls. Do not enable live recording until every blocker applicable to the selected product mode and launch jurisdiction is closed with evidence.
