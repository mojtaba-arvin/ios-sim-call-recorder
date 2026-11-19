# Contributing

## Branching

Never commit directly to `main`. Create a focused branch from the latest `main`:

- `feat/<short-description>` — product capability
- `fix/<short-description>` — defect correction
- `docs/<short-description>` — documentation and research
- `ci/<short-description>` — CI and repository automation
- `test/<short-description>` — test infrastructure or coverage
- `research/<short-description>` — isolated feasibility experiments

Keep branches short-lived and scoped to one reviewable outcome.

## Commits

Use Conventional Commits:

- `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `ci:`, `build:`, `chore:`
- Imperative subject, concise and specific.
- Separate unrelated changes into separate commits.
- Do not include generated files, secrets, personal call recordings or unredacted diagnostics.

## Pull requests

- Open a Draft PR early when feedback is useful; mark it ready only when its scope is reviewable.
- Explain problem, approach, alternatives, risks, validation and compatibility impact.
- Link issues and attach reproducible evidence for device/carrier behavior.
- State clearly whether claims are confirmed, observed, hypothetical or rejected.
- Do not merge with failing required checks or unresolved high-impact review comments.
- Use the repository-approved merge strategy. Do not squash a dependency stack when doing so would erase prerequisite ancestry or make downstream review ambiguous.

## Testing and evidence

- Simulator-only success is not proof of cellular call audio capture.
- Record exact device identifier, iOS version/build, region, carrier/plan, SIM, network, call scenario and audio route.
- Verify local and remote audio independently.
- Include failure cases and repeat counts; do not report only successful runs.
- Never upload real call content without informed consent and an approved secure test procedure.

## Security and privacy

Never commit credentials, provisioning profiles, private keys, personal data or raw recordings. Use synthetic fixtures by default. Report vulnerabilities privately to the repository owner rather than publishing exploit details in an issue.
