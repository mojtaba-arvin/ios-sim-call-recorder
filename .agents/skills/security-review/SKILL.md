---
name: security-review
description: Perform threat-focused review of privacy, consent, file handling, API/provider trust, secrets, CI permissions and data retention.
---

# Security review

## Procedure
1. Enumerate assets, actors, trust boundaries and sensitive data.
2. Trace recording and metadata from import/capture through storage, export, provider APIs, logs and deletion.
3. Verify consent is evidence-backed and cannot be forged by a caller-controlled field.
4. Test path traversal, malformed media, oversized inputs, symlinks, archive expansion and unsafe cleanup.
5. Review authn/authz, tenant boundaries, webhook signature and replay defenses.
6. Inspect secret storage, redaction, telemetry, CI artifacts and third-party transfers.
7. Review GitHub workflow permissions, action pinning, checkout credential persistence and untrusted code execution.
8. Classify findings and specify reproducible abuse cases and mitigations.

## Output
- Threat-model delta.
- Findings with severity, path/line, preconditions, impact and remediation.
- Residual risk and untested areas.

## Completion gate
P0/P1 findings block readiness; privacy and consent limitations are explicitly documented.


## Telephony payload privacy regression

- Treat `from`, `to`, `source`, `destination`, `caller`, `callee`, `number`, E.164 and equivalent normalized/nested keys as potentially phone-number-bearing fields.
- Prefer explicit command payload allowlists over relying only on a key denylist; key checks cannot detect PII hidden under arbitrary innocent-looking keys.
- Ensure invalid outbox commands are rejected before provider reconciliation/execution and do not create remote resources.
- Add nested payload regression tests and assert the provider adapter is not called for invalid commands.
