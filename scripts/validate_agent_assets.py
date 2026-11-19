#!/usr/bin/env python3
"""Dependency-free structural validation for repository agent roles and skills."""
from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED_ROLES = {
    "product-architect.md",
    "researcher.md",
    "implementer.md",
    "reviewer.md",
    "validator.md",
    "security-reviewer.md",
    "documentation-agent.md",
}
REQUIRED_SKILLS = {
    "git-history-analysis",
    "architecture-review",
    "ios-validation",
    "backend-validation",
    "security-review",
    "evidence-management",
}
REQUIRED_TEMPLATES = {"task.md", "adr.md", "test-report.md"}
REQUIRED_POLICIES = {"evidence-levels.md", "privacy.md", "branch-management.md"}


def validate_agent_assets(root: Path) -> list[str]:
    errors: list[str] = []
    roles = root / ".agents" / "roles"
    skills = root / ".agents" / "skills"
    templates = root / ".agents" / "templates"
    policies = root / ".agents" / "policies"

    for directory, expected, label in (
        (roles, REQUIRED_ROLES, "role"),
        (templates, REQUIRED_TEMPLATES, "template"),
        (policies, REQUIRED_POLICIES, "policy"),
    ):
        missing = sorted(name for name in expected if not (directory / name).is_file())
        errors.extend(f"{label} missing: {directory.relative_to(root) / name}" for name in missing)

    for name in sorted(REQUIRED_ROLES):
        path = roles / name
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        if not content.startswith("# "):
            errors.append(f"role must start with a Markdown heading: {path.relative_to(root)}")
        if "Deliverable:" not in content:
            errors.append(f"role must define a deliverable: {path.relative_to(root)}")

    for name in sorted(REQUIRED_SKILLS):
        path = skills / name / "SKILL.md"
        if not path.is_file():
            errors.append(f"skill missing: {path.relative_to(root)}")
            continue
        content = path.read_text(encoding="utf-8")
        front_matter = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
        if not front_matter:
            errors.append(f"skill must have YAML front matter: {path.relative_to(root)}")
            continue
        metadata = front_matter.group(1)
        declared_name = re.search(r"(?m)^name:\s*([a-z0-9-]+)\s*$", metadata)
        description = re.search(r"(?m)^description:\s*\S.+$", metadata)
        if not declared_name or declared_name.group(1) != name:
            errors.append(f"skill name must match directory '{name}': {path.relative_to(root)}")
        if not description:
            errors.append(f"skill must have a non-empty description: {path.relative_to(root)}")
        for heading in ("# ", "## Procedure", "## Output", "## Completion gate"):
            if heading not in content:
                errors.append(f"skill missing required section '{heading}': {path.relative_to(root)}")

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate_agent_assets(root)
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    print(
        f"Validated {len(REQUIRED_ROLES)} roles, {len(REQUIRED_SKILLS)} skills, "
        f"{len(REQUIRED_TEMPLATES)} templates and {len(REQUIRED_POLICIES)} policies."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
