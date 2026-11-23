# Execution Decisions

These are conservative, reversible execution defaults for the 2026-11-23 engineering session. They do not override accepted ADRs or grant production authority.

## D-EXEC-001 — Keep release blocked
**Decision:** Keep release status BLOCKED until repository governance, real provider acceptance, physical-device/carrier evidence, AWS staging evidence and jurisdiction-specific legal/privacy approval are all present.  
**Reason:** CI, simulator behavior and source review cannot establish those external facts.  
**Revisit:** Only with independently reviewable evidence for each gate.

## D-EXEC-002 — Do not apply privileged or paid operations
**Decision:** Prepare scripts, payloads, validation and plans only. Do not mutate Rulesets through an unverified path, create AWS resources, incur Twilio charges, or deploy production/staging resources without explicit authorization.  
**Reason:** The connected GitHub API surface provides ruleset reads but no supported ruleset write action; AWS/Twilio account authority and budget are not established.  
**Revisit:** After a human administrator/operator executes the reviewed action and the resulting state is read back.

## D-EXEC-003 — Preserve pathway distinctions
**Decision:** Treat native SIM-call merge, app-owned Twilio Conference, imported audio and app-owned VoIP as separate product pathways. Never use one pathway's tests to claim another pathway's capability.  
**Reason:** The current Twilio Conference is app-owned outbound calling and does not prove access to native Phone.app audio.  
**Revisit:** Only with exact physical-device and provider evidence.

## D-EXEC-004 — Evidence tiers remain explicit
**Decision:** Label source review, unit/integration, simulator, physical-device, carrier and live-provider evidence separately. Never infer exactly-once remote execution from database idempotency.  
**Reason:** Provider side effects and physical carrier topology are external systems.  
**Revisit:** Per capability, with evidence attached to the exact commit/configuration.
