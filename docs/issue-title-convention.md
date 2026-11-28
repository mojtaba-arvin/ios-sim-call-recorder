# GitHub Issue title convention

Use this format for every GitHub Issue title:

`<type>(<scope>): <short, clear description>`

## Type

Choose one lowercase Conventional Commit type:

- `feat` — new capability
- `fix` — defect correction
- `docs` — documentation
- `refactor` — behavior-preserving restructuring
- `test` — tests and test infrastructure
- `build` — build and packaging
- `ci` — continuous integration
- `chore` — maintenance and repository housekeeping
- `perf` — performance improvement
- `revert` — revert a prior change

## Scope and description

- Use a concise lowercase kebab-case scope naming the affected domain or component (for example, `consent`, `audio-import`, `privacy`, or `release`).
- Write a short, clear description of the requested outcome. Prefer specific wording over internal shorthand.
- Keep the title readable and focused on one issue.

## Metadata belongs outside the title

Keep priority, milestones, feature or command IDs, phase identifiers, dates, agent identity, and run metadata in GitHub labels, milestone fields, or the Issue body. Do not add bracketed prefixes, standalone priority codes, `Recover:`, or agent/supervisor identity prefixes to titles.

When renaming an existing Issue, change only its title; preserve labels, milestone, assignees, body, comments, and relationships.

## Examples

- `docs(governance): adopt canonical issue title convention`
- `fix(consent): reject unverified participant approval`
- `test(audio-import): cover malformed wav boundaries`
- `chore(release): clarify physical-device acceptance gates`

This convention governs Issue titles only. Commit messages continue to follow the Conventional Commits policy in [AGENTS.md](../AGENTS.md).

## iOS project constraints

A title convention does not relax project policy. Issues and their implementation must continue to respect participant consent, privacy and data minimization, the prohibition on private-API cellular interception, and the distinction between simulator, integration, carrier, and physical-device evidence. Do not describe simulator results as physical-device validation or imply that a release is ready without the documented release gates.
