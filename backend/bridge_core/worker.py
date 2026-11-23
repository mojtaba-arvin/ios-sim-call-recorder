# Graceful, bounded polling loop around the lease-based outbox dispatcher.
from __future__ import annotations
import logging
import threading
from dataclasses import dataclass

LOGGER = logging.getLogger('bridge.worker')

@dataclass(frozen=True, slots=True)
class WorkerCycle:
    claimed: int
    acknowledged: int
    deferred: int

class SupervisedOutboxWorker:
    def __init__(self, *, dispatcher, worker_id: str, poll_interval_seconds: float = 1.0, batch_size: int = 10):
        if not worker_id or not worker_id.strip(): raise ValueError('worker_id is required')
        if not 0.1 <= poll_interval_seconds <= 60: raise ValueError('poll interval must be between 0.1 and 60 seconds')
        if not 1 <= batch_size <= 100: raise ValueError('batch size must be between 1 and 100')
        self.dispatcher = dispatcher
        self.worker_id = worker_id
        self.poll_interval_seconds = poll_interval_seconds
        self.batch_size = batch_size
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run_once(self) -> WorkerCycle:
        results = self.dispatcher.dispatch_once(limit=self.batch_size)
        acknowledged = sum(1 for item in results if item.outcome == 'acknowledged')
        deferred = len(results) - acknowledged
        return WorkerCycle(len(results), acknowledged, deferred)

    def run_forever(self) -> None:
        LOGGER.info('worker_started worker_id=%s', self.worker_id)
        while not self._stop.is_set():
            try:
                cycle = self.run_once()
                if cycle.claimed:
                    LOGGER.info('worker_cycle worker_id=%s claimed=%d acknowledged=%d deferred=%d duration_ms=%d',
                                self.worker_id, cycle.claimed, cycle.acknowledged, cycle.deferred, cycle.duration_ms)
            except Exception:
                # Do not emit exception text: adapters may accidentally include
                # provider request values in exceptions.
                LOGGER.error('worker_cycle_failed worker_id=%s', self.worker_id)
            self._stop.wait(self.poll_interval_seconds)
        LOGGER.info('worker_stopped worker_id=%s', self.worker_id)
