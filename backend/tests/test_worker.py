import unittest
from bridge_core.worker import SupervisedOutboxWorker

class FakeDispatcher:
    def __init__(self, worker=None): self.calls=0; self.worker=worker
    def dispatch_once(self, *, limit):
        self.calls += 1
        if self.worker and self.calls == 2: self.worker.stop()
        return ()

class WorkerTests(unittest.TestCase):
    def test_worker_stops_after_signal_between_cycles(self):
        dispatcher=FakeDispatcher()
        worker=SupervisedOutboxWorker(dispatcher=dispatcher,worker_id='worker-test',poll_interval_seconds=0.1)
        dispatcher.worker=worker
        worker.run_forever()
        self.assertEqual(dispatcher.calls,2)

    def test_invalid_poll_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            SupervisedOutboxWorker(dispatcher=FakeDispatcher(),worker_id='worker-test',poll_interval_seconds=0)

if __name__=='__main__': unittest.main()
