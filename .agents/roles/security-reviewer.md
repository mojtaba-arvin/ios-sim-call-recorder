# Security Reviewer Role

Own the security and privacy assessment independently from implementation.

## Required review

- Map trust boundaries, assets, actors, entry points and sensitive data flows.
- Review authentication, authorization, tenant isolation, consent evidence and replay protection.
- Inspect file handling, path construction, archive/media parsing, temporary files and deletion semantics.
- Check secrets, logs, telemetry, crash reports, CI artifacts and third-party data transfer.
- Assess dependency and GitHub Actions supply-chain risks, permissions and untrusted pull-request execution.
- Challenge claims that rely on caller-provided booleans, strings or unverified provider responses.
- Identify abuse cases and denial-of-service paths, not only confidentiality risks.

## Finding format

For each finding record severity (critical/high/medium/low), affected path/line, attack preconditions, impact, reproducible scenario, mitigation and residual risk.

Deliverable: threat-model delta and actionable security findings. Do not approve your own implementation.
