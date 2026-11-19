from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validate_agent_assets import (
    REQUIRED_POLICIES,
    REQUIRED_ROLES,
    REQUIRED_SKILLS,
    REQUIRED_TEMPLATES,
    validate_agent_assets,
)


class AgentAssetValidatorTests(unittest.TestCase):
    def make_valid_tree(self, root: Path) -> None:
        roles = root / ".agents" / "roles"
        skills = root / ".agents" / "skills"
        templates = root / ".agents" / "templates"
        policies = root / ".agents" / "policies"
        for directory in (roles, skills, templates, policies):
            directory.mkdir(parents=True, exist_ok=True)

        for name in REQUIRED_ROLES:
            (roles / name).write_text("# Role\n\nDeliverable: report\n", encoding="utf-8")
        for name in REQUIRED_SKILLS:
            directory = skills / name
            directory.mkdir(parents=True)
            (directory / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: Validate {name} behavior.\n---\n"
                "# Skill\n\n## Procedure\n1. Inspect.\n\n## Output\nReport.\n\n"
                "## Completion gate\nPass.\n",
                encoding="utf-8",
            )
        for name in REQUIRED_TEMPLATES:
            (templates / name).write_text("# Template\n", encoding="utf-8")
        for name in REQUIRED_POLICIES:
            (policies / name).write_text("# Policy\n", encoding="utf-8")

    def test_accepts_complete_agent_asset_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.make_valid_tree(root)
            self.assertEqual(validate_agent_assets(root), [])

    def test_rejects_skill_without_front_matter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.make_valid_tree(root)
            skill = root / ".agents" / "skills" / "ios-validation" / "SKILL.md"
            skill.write_text("# Missing metadata\n", encoding="utf-8")
            errors = validate_agent_assets(root)
            self.assertTrue(any("YAML front matter" in error for error in errors))

    def test_rejects_skill_name_that_does_not_match_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.make_valid_tree(root)
            skill = root / ".agents" / "skills" / "ios-validation" / "SKILL.md"
            skill.write_text(
                "---\nname: wrong-name\ndescription: Test.\n---\n"
                "# Skill\n## Procedure\n## Output\n## Completion gate\n",
                encoding="utf-8",
            )
            errors = validate_agent_assets(root)
            self.assertTrue(any("must match directory" in error for error in errors))

    def test_rejects_role_without_deliverable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.make_valid_tree(root)
            role = root / ".agents" / "roles" / "reviewer.md"
            role.write_text("# Reviewer\nNo output contract.\n", encoding="utf-8")
            errors = validate_agent_assets(root)
            self.assertTrue(any("define a deliverable" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
