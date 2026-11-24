"""Graceful, bounded polling loop around the lease-based outbox dispatcher."""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from time import monotonic_ns

LOGGER = logging.getLogger("bridge.worker")


@dataclass(frozen=True, slots=True)
class WorkerCycle:
    claimed: int
    acknowledged: int
    deferred: int
    duration_ms: int


class SupervisedOutboxWorker:
    def __init__(
        self,
        *,
        dispatcher,
        worker_id: str,
        poll_interval_seconds: float = 1.0,
        batch_size: int = 1,
    ):
        if not worker_id or not worker_id.strip():
            raise ValueError("worker_id is required")
        if not 0.1 <= poll_interval_seconds <= 60:
            raise ValueError("poll interval must be between 0.1 and 60 seconds")
        if not 1 <= batch_size <= 100:
            raise ValueError("batch size must be between 1 and 100")
        self.dispatcher = dispatcher
        self.worker_id = worker_id
        self.poll_interval_seconds = poll_interval_seconds
        self.batch_size = batch_size
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run_once(self) -> WorkerCycle:
        started_ns = monotonic_ns()
        results = self.dispatcher.dispatch_once(limit=self.batch_size)
        acknowledged = sum(1 for item in results if item.outcome == "acknowledged")
        deferred = len(results) - acknowledged
        duration_ms = max(0, (monotonic_ns() - started_ns) // 1_000_000)
        return WorkerCycle(len(results), acknowledged, deferred, duration_ms)

    def run_forever(self) -> None:
        heartbeat_interval_ns = 30_000_000_000
        last_heartbeat_ns = monotonic_ns()
        LOGGER.info("worker_started worker_id=%s", self.worker_id)
        while not self._stop.is_set():
            try:
                cycle = self.run_once()
                now_ns = monotonic_ns()
                if cycle.claimed:
                    LOGGER.info(
                        "worker_cycle worker_id=%s claimed=%d acknowledged=%d deferred=%d duration_ms=%d",
                        self.worker_id,
                        cycle.claimed,
                        cycle.acknowledged,
                        cycle.deferred,
                        cycle.duration_ms,
                    )
                    last_heartbeat_ns = now_ns
                elif now_ns - last_heartbeat_ns >= heartbeat_interval_ns:
                    # Empty queues are healthy, but without an idle heartbeat an
                    # operator cannot distinguish an idle worker from a dead one.
                    LOGGER.info(
                        "worker_heartbeat worker_id=%s idle=true duration_ms=%d",
                        self.worker_id,
                        cycle.duration_ms,
                    )
                    last_heartbeat_ns = now_ns
            except Exception:
                # Do not emit exception text: adapters may accidentally include
                # provider request values in exceptions.
                LOGGER.error("worker_cycle_failed worker_id=%s", self.worker_id)
            self._stop.wait(self.poll_interval_seconds)
        LOGGER.info("worker_stopped worker_id=%s", self.worker_id)
