from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from bridge_core.config import bounded_float_from_env


class BoundedFloatFromEnvTests(unittest.TestCase):
    def test_uses_default_when_setting_is_absent(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                bounded_float_from_env(
                    "TWILIO_REQUEST_TIMEOUT_SECONDS",
                    10.0,
                    minimum=1.0,
                    maximum=12.0,
                ),
                10.0,
            )

    def test_reads_valid_override(self):
        with patch.dict(os.environ, {"TWILIO_REQUEST_TIMEOUT_SECONDS": "4.5"}, clear=True):
            self.assertEqual(
                bounded_float_from_env(
                    "TWILIO_REQUEST_TIMEOUT_SECONDS",
                    10.0,
                    minimum=1.0,
                    maximum=12.0,
                ),
                4.5,
            )

    def test_rejects_non_numeric_and_out_of_range_values(self):
        for raw in ("not-a-number", "0.9", "12.1", "nan", "inf"):
            with self.subTest(value=raw):
                with patch.dict(os.environ, {"TWILIO_REQUEST_TIMEOUT_SECONDS": raw}, clear=True):
                    with self.assertRaises(RuntimeError):
                        bounded_float_from_env(
                            "TWILIO_REQUEST_TIMEOUT_SECONDS",
                            10.0,
                            minimum=1.0,
                            maximum=12.0,
                        )


if __name__ == "__main__":
    unittest.main()
