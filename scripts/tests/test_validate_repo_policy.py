from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VALID_ACTION_SHA = "a" * 40


class RepositoryPolicyValidatorTests(unittest.TestCase):
    def run_validator(self, workflow: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            scripts_directory = root / "scripts"
            workflows_directory = root / ".github" / "workflows"
            scripts_directory.mkdir(parents=True)
            workflows_directory.mkdir(parents=True)

            shutil.copy2(
                REPOSITORY_ROOT / "scripts" / "validate_repo_policy.py",
                scripts_directory / "validate_repo_policy.py",
            )
            (workflows_directory / "test.yml").write_text(workflow, encoding="utf-8")

            return subprocess.run(
                [sys.executable, str(scripts_directory / "validate_repo_policy.py")],
                check=False,
                capture_output=True,
                text=True,
            )

    def valid_workflow(self) -> str:
        return f"""name: policy-fixture

on:
  pull_request:

permissions:
  contents: read

concurrency:
  group: policy-fixture-${{{{ github.ref }}}}
  cancel-in-progress: true

jobs:
  checks:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Checkout
        uses: actions/checkout@{VALID_ACTION_SHA}
"""

    def test_accepts_explicit_read_only_permissions_and_pinned_actions(self) -> None:
        result = self.run_validator(self.valid_workflow())
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_top_level_write_permission(self) -> None:
        workflow = self.valid_workflow().replace(
            "  contents: read",
            "  contents: write",
        )
        result = self.run_validator(workflow)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("write permission (contents)", result.stderr)

    def test_rejects_job_level_write_permission(self) -> None:
        workflow = self.valid_workflow().replace(
            "    runs-on: ubuntu-latest",
            "    permissions:\n      actions: write\n    runs-on: ubuntu-latest",
        )
        result = self.run_validator(workflow)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("write permission (actions)", result.stderr)

    def test_rejects_unpinned_actions(self) -> None:
        workflow = self.valid_workflow().replace(
            f"actions/checkout@{VALID_ACTION_SHA}",
            "actions/checkout@v4",
        )
        result = self.run_validator(workflow)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("full 40-character SHA", result.stderr)

    def test_rejects_jobs_without_timeouts(self) -> None:
        workflow = self.valid_workflow().replace("    timeout-minutes: 5\n", "")
        result = self.run_validator(workflow)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing timeout-minutes", result.stderr)


if __name__ == "__main__":
    unittest.main()
