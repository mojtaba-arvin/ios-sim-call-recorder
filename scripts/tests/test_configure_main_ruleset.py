from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "configure-main-ruleset.sh"
PAYLOAD = ROOT / "docs" / "governance" / "main-ruleset-payload.json"

REQUIRED_CHECKS = {
    "backend-postgres (PostgreSQL 16)",
    "backend-postgres (PostgreSQL 17)",
    "swift-core",
    "xctest (iPhone 16)",
    "xctest (iPhone 16 Pro)",
    "audio-analyzer",
    "terraform-validate",
    "repository-policy",
}


class MainRulesetScriptTests(unittest.TestCase):
    def test_requires_exact_canonical_release_preflight_checks(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        for check in REQUIRED_CHECKS:
            with self.subTest(check=check):
                self.assertIn(f'"context": "{check}"', script)

    def test_canonical_payload_matches_main_protection_contract(self) -> None:
        payload = json.loads(PAYLOAD.read_text(encoding="utf-8"))
        self.assertEqual(payload["name"], "protect main")
        self.assertEqual(payload["target"], "branch")
        self.assertEqual(payload["enforcement"], "active")
        self.assertEqual(payload["bypass_actors"], [])
        self.assertEqual(
            payload["conditions"]["ref_name"]["include"],
            ["refs/heads/main"],
        )
        rules = {rule["type"]: rule for rule in payload["rules"]}
        self.assertTrue({
            "deletion",
            "non_fast_forward",
            "required_linear_history",
            "pull_request",
            "required_conversation_resolution",
            "required_status_checks",
        }.issubset(rules))
        contexts = {
            item["context"]
            for item in rules["required_status_checks"]["parameters"]["required_status_checks"]
        }
        self.assertEqual(contexts, REQUIRED_CHECKS)
        self.assertTrue(
            rules["required_status_checks"]["parameters"]["strict_required_status_checks_policy"]
        )

    def test_rejects_legacy_check_names(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        for legacy in (
            "Repository policy integrity",
            "Conference bridge backend tests",
            "CallRecorderApp simulator build",
            "CallRecorderCore tests",
            "Audio quality analyzer tests",
            "AWS Terraform validation",
        ):
            with self.subTest(legacy=legacy):
                self.assertNotIn(legacy, script)

    def test_preserves_branch_safety_and_empty_bypass(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        for required in (
            '"bypass_actors": []',
            '"type": "deletion"',
            '"type": "non_fast_forward"',
            '"type": "required_linear_history"',
            '"type": "pull_request"',
            '"type": "required_conversation_resolution"',
            '"type": "required_status_checks"',
        ):
            with self.subTest(required=required):
                self.assertIn(required, script)


if __name__ == "__main__":
    unittest.main()
