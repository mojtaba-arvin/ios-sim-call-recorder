from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools.twilio_live_acceptance import HarnessError, _E164, run


class TwilioLiveHarnessTests(unittest.TestCase):
    def test_dry_run_is_inert_without_environment_or_network(self):
        with patch.dict(os.environ, {}, clear=True):
            result = run(SimpleNamespace(execute=False))
        self.assertEqual(result["status"], "dry-run")
        self.assertIn("No API request", result["message"])

    def test_e164_validation_accepts_international_numbers_only(self):
        self.assertTrue(_E164.fullmatch("+14155550123"))
        self.assertTrue(_E164.fullmatch("+442079460123"))
        self.assertFalse(_E164.fullmatch("4155550123"))
        self.assertFalse(_E164.fullmatch("+0123456789"))
        self.assertFalse(_E164.fullmatch("+14155550123456789"))

    def test_live_execution_requires_explicit_staging_approval(self):
        with patch.dict(os.environ, {"BRIDGE_ENVIRONMENT": "production"}, clear=True):
            with self.assertRaisesRegex(HarnessError, "staging"):
                run(SimpleNamespace(execute=True, timeout_seconds=900, expect_state="completed"))

    def test_live_execution_requires_separate_approval_flag(self):
        with patch.dict(os.environ, {
            "BRIDGE_ENVIRONMENT": "staging",
            "TWILIO_LIVE_TEST_APPROVED": "false",
        }, clear=True):
            with self.assertRaisesRegex(HarnessError, "TWILIO_LIVE_TEST_APPROVED"):
                run(SimpleNamespace(execute=True, timeout_seconds=900, expect_state="completed"))


if __name__ == "__main__":
    unittest.main()