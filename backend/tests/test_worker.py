import unittest
from pathlib import Path
from unittest.mock import patch

from bridge_core.worker import SupervisedOutboxWorker


class Result:
    def __init__(self, outcome):
        self.outcome = outcome


class FakeDispatcher:
    def __init__(self, outcomes=(), worker=None):
        self.outcomes = outcomes
        self.worker = worker
        self.calls = 0
        self.limits = []

    def dispatch_once(self, *, limit):
        self.calls += 1
        self.limits.append(limit)
        if self.worker and self.calls == 2:
            self.worker.stop()
        return self.outcomes[:limit]


class WorkerTests(unittest.TestCase):
    def test_worker_stops_after_signal_between_cycles(self):
        dispatcher = FakeDispatcher()
        worker = SupervisedOutboxWorker(
            dispatcher=dispatcher,
            worker_id="worker-test",
            poll_interval_seconds=0.1,
        )
        dispatcher.worker = worker
        worker.run_forever()
        self.assertEqual(dispatcher.calls, 2)

    def test_idle_worker_emits_periodic_heartbeat(self):
        dispatcher = FakeDispatcher()
        worker = SupervisedOutboxWorker(
            dispatcher=dispatcher,
            worker_id="worker-test",
            poll_interval_seconds=0.1,
        )
        dispatcher.worker = worker
        # Initial timestamp, first cycle start/end/check, then second cycle
        # start/end/check. The first post-cycle check crosses the 30s interval.
        clock = iter((0, 1, 2, 30_000_000_001, 30_000_000_002,
                      30_000_000_003, 30_000_000_004))
        with patch("bridge_core.worker.monotonic_ns", side_effect=lambda: next(clock)):
            with self.assertLogs("bridge.worker", level="INFO") as captured:
                worker.run_forever()
        self.assertTrue(any("worker_heartbeat worker_id=worker-test idle=true" in line
                            for line in captured.output))
        self.assertEqual(dispatcher.calls, 2)

    def test_invalid_poll_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            SupervisedOutboxWorker(
                dispatcher=FakeDispatcher(),
                worker_id="worker-test",
                poll_interval_seconds=0,
            )

    def test_run_once_reports_counts_and_cycle_duration(self):
        dispatcher = FakeDispatcher([
            Result("acknowledged"),
            Result("deferred"),
            Result("reconciliation_required"),
        ])
        worker = SupervisedOutboxWorker(
            dispatcher=dispatcher,
            worker_id="worker-test",
            batch_size=1,
        )

        cycle = worker.run_once()

        self.assertEqual(dispatcher.limits, [1])
        self.assertEqual(cycle.claimed, 1)
        self.assertEqual(cycle.acknowledged, 1)
        self.assertEqual(cycle.deferred, 0)
        self.assertGreaterEqual(cycle.duration_ms, 0)

    def test_empty_cycle_reports_zero_counts(self):
        worker = SupervisedOutboxWorker(
            dispatcher=FakeDispatcher(),
            worker_id="worker-test",
        )

        cycle = worker.run_once()

        self.assertEqual(cycle.claimed, 0)
        self.assertEqual(cycle.acknowledged, 0)
        self.assertEqual(cycle.deferred, 0)
        self.assertGreaterEqual(cycle.duration_ms, 0)

    def test_production_entrypoint_defaults_batch_size_to_one(self):
        entrypoint = Path(__file__).resolve().parents[1] / "worker_main.py"
        source = entrypoint.read_text(encoding="utf-8")
        self.assertIn('os.environ.get("WORKER_BATCH_SIZE", "1")', source)

    def test_default_batch_size_is_single_command(self):
        worker = SupervisedOutboxWorker(
            dispatcher=FakeDispatcher(),
            worker_id="worker-test",
        )
        self.assertEqual(worker.batch_size, 1)

    def test_batch_size_is_bounded(self):
        for invalid in (0, 101):
            with self.subTest(batch_size=invalid):
                with self.assertRaises(ValueError):
                    SupervisedOutboxWorker(
                        dispatcher=FakeDispatcher(),
                        worker_id="worker-test",
                        batch_size=invalid,
                    )


if __name__ == "__main__":
    unittest.main()
