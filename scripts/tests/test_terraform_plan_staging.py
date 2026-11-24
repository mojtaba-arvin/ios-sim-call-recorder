from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "infra" / "aws" / "plan-staging.sh"


class TerraformPlanOnlyScriptTests(unittest.TestCase):
    def test_requires_explicit_account_and_region_guard(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("EXPECTED_AWS_ACCOUNT_ID", script)
        self.assertIn("AWS_REGION", script)
        self.assertIn("aws sts get-caller-identity", script)
        self.assertIn('if [[ "$ACTUAL_ACCOUNT" != "$EXPECTED_AWS_ACCOUNT_ID" ]]', script)
        self.assertIn('-var="region=$AWS_REGION"', script)

    def test_runs_plan_only_without_apply_or_destroy(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("terraform -chdir=infra/aws plan", script)
        self.assertIn("terraform -chdir=infra/aws show", script)
        self.assertIn("trap cleanup EXIT", script)
        commands = re.findall(r"^\s*terraform\b.*$", script, flags=re.MULTILINE)
        self.assertTrue(commands)
        self.assertFalse(any(re.search(r"\b(apply|destroy)\b", line) for line in commands))

    def test_initialization_disables_remote_backend(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("init -backend=false -input=false", script)


if __name__ == "__main__":
    unittest.main()
