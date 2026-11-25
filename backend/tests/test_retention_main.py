from __future__ import annotations

import logging
import unittest
from uuid import uuid4
from unittest.mock import Mock

from providers.twilio.media import TwilioMediaRetentionWorker
from retention_main import run_cycle


class RetentionCycleTests(unittest.TestCase):
    def test_success_emits_counts_and_duration(self):
        ingestor = Mock()
        ingestor.recover_once.return_value = 2
        worker = Mock()
        worker.run_once.return_value = 3
        log = Mock()
        ticks = iter((10.0, 10.25))

        self.assertTrue(run_cycle(ingestor, worker, clock=lambda: next(ticks), log=log))

        log.info.assert_called_once_with(
            "retention_cycle_completed",
            extra={"recovered_ingestions": 2, "deleted_assets": 3, "duration_ms": 250},
        )
        log.error.assert_not_called()

    def test_failure_logs_type_without_exception_message(self):
        ingestor = Mock()
        ingestor.recover_once.side_effect = RuntimeError("secret-url-and-provider-id")
        log = Mock()
        ticks = iter((1.0, 1.5))

        self.assertFalse(run_cycle(ingestor, Mock(), clock=lambda: next(ticks), log=log))

        log.error.assert_called_once_with(
            "retention_cycle_failed",
            extra={"error_type": "RuntimeError", "duration_ms": 500},
        )
        log.info.assert_not_called()


class RetryTelemetryTests(unittest.TestCase):
    class Cursor:
        rowcount = 1
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def execute(self, query, params):
            self.query, self.params = query, params

    class Connection:
        def __init__(self):
            self.cursor_instance = RetryTelemetryTests.Cursor()
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def cursor(self):
            return self.cursor_instance

    def test_retry_event_contains_only_safe_dimensions(self):
        connection = self.Connection()
        worker = TwilioMediaRetentionWorker(
            connect=lambda: connection, client=object(), object_store=object(),
        )
        token = str(uuid4())

        with self.assertLogs("providers.twilio.media", level="WARNING") as captured:
            worker._schedule_retry(
                "opaque-media-id", token,
                RuntimeError("secret-url-and-provider-id"), stage="object_storage",
            )

        self.assertEqual(len(captured.records), 1)
        record = captured.records[0]
        self.assertEqual(record.getMessage(), "retention_delete_retry_scheduled")
        self.assertEqual(record.stage, "object_storage")
        self.assertEqual(record.error_type, "RuntimeError")
        self.assertNotIn("secret-url-and-provider-id", captured.output[0])
        self.assertNotIn("opaque-media-id", captured.output[0])
        self.assertNotIn(token, captured.output[0])


if __name__ == "__main__":
    unittest.main()
