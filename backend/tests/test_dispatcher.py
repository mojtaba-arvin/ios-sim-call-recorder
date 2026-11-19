from __future__ import annotations

import unittest
from datetime import datetime, timezone
from uuid import uuid4

from bridge_core.dispatcher import (
    OutboxCommandDispatcher,
    ProviderExecutionResult,
    ProviderOperationError,
    ReconciliationResult,
    ReconciliationState,
)
from bridge_core.persistence import LeasedCommand


class FakeRepository:
    def __init__(self, commands):
        self.commands = tuple(commands)
        self.resources = {}
        self.participant_resources = {}
        self.acked = []
        self.failed = []

    def claim_outbox(self, **kwargs):
        commands, self.commands = self.commands, ()
        return commands

    def get_provider_resource(self, provider, account, session):
        return self.resources.get((provider, account, session))

    def put_provider_resource(self, provider, account, session, conference_sid):
        key = (provider, account, session)
        existing = self.resources.get(key)
        if existing is not None and existing != conference_sid:
            raise AssertionError("resource mapping must be immutable")
        self.resources[key] = conference_sid

    def get_provider_participant_resource(self, provider, account, session, participant_ref):
        return self.participant_resources.get((provider, account, session, participant_ref))

    def put_provider_participant_resource(self, provider, account, session, participant_ref, call_sid):
        key = (provider, account, session, participant_ref)
        existing = self.participant_resources.get(key)
        if existing is not None and existing != call_sid:
            raise AssertionError("participant mapping must be immutable")
        self.participant_resources[key] = call_sid

    def acknowledge_outbox(self, command_id, lease_token):
        self.acked.append((command_id, lease_token))

    def fail_outbox(self, command_id, lease_token, *, error_code, retry_delay_seconds):
        self.failed.append((command_id, lease_token, error_code, retry_delay_seconds))
        return "pending"


class FakeAdapter:
    def __init__(self, reconciliation, execution=None):
        self.reconciliation = reconciliation
        self.execution = execution or ProviderExecutionResult()
        self.reconcile_calls = []
        self.execute_calls = []

    def reconcile(self, command, *, conference_sid, call_sid):
        self.reconcile_calls.append((command, conference_sid, call_sid))
        return self.reconciliation

    def execute(self, command, *, conference_sid, call_sid):
        self.execute_calls.append((command, conference_sid, call_sid))
        return self.execution


def leased_command():
    return LeasedCommand(
        command_id=uuid4(),
        command_type="recording.start",
        idempotency_key="recording-start:twilio:account-opaque:session-opaque",
        session_id="session-opaque",
        provider="twilio",
        provider_account_id="account-opaque",
        payload={"session_id": "session-opaque"},
        attempts=1,
        lease_token=uuid4(),
        lease_owner="worker-test",
        lease_expires_at=datetime.now(timezone.utc),
    )


class DispatcherTests(unittest.TestCase):
    def test_unknown_provider_outcome_is_deferred_without_replaying_side_effect(self):
        command = leased_command()
        repo = FakeRepository([command])
        adapter = FakeAdapter(ReconciliationResult(ReconciliationState.UNKNOWN))
        dispatcher = OutboxCommandDispatcher(
            repository=repo, adapters={("twilio", "account-opaque"): adapter},
            worker_id="worker-test",
        )

        results = dispatcher.dispatch_once()

        self.assertEqual(results[0].outcome, "reconciliation_required")
        self.assertEqual(adapter.execute_calls, [])
        self.assertEqual(repo.acked, [])
        self.assertEqual(repo.failed[0][2], "provider_outcome_unknown")

    def test_not_applied_executes_then_persists_resource_before_ack(self):
        command = leased_command()
        repo = FakeRepository([command])
        adapter = FakeAdapter(
            ReconciliationResult(ReconciliationState.NOT_APPLIED),
            ProviderExecutionResult(conference_sid="CF" + "a" * 32),
        )
        dispatcher = OutboxCommandDispatcher(
            repository=repo, adapters={("twilio", "account-opaque"): adapter},
            worker_id="worker-test",
        )

        results = dispatcher.dispatch_once()

        self.assertEqual(results[0].outcome, "acknowledged")
        self.assertEqual(len(adapter.execute_calls), 1)
        self.assertEqual(repo.resources[("twilio", "account-opaque", "session-opaque")],
                         "CF" + "a" * 32)
        self.assertEqual(len(repo.acked), 1)

    def test_applied_reconciliation_skips_execute_and_persists_discovered_resource(self):
        command = leased_command()
        repo = FakeRepository([command])
        adapter = FakeAdapter(ReconciliationResult(
            ReconciliationState.APPLIED, conference_sid="CF" + "b" * 32,
        ))
        dispatcher = OutboxCommandDispatcher(
            repository=repo, adapters={("twilio", "account-opaque"): adapter},
            worker_id="worker-test",
        )

        results = dispatcher.dispatch_once()

        self.assertEqual(results[0].outcome, "acknowledged")
        self.assertEqual(adapter.execute_calls, [])
        self.assertEqual(repo.resources[("twilio", "account-opaque", "session-opaque")],
                         "CF" + "b" * 32)
        self.assertEqual(len(repo.acked), 1)

    def test_existing_resource_is_supplied_to_reconciliation(self):
        command = leased_command()
        repo = FakeRepository([command])
        repo.resources[("twilio", "account-opaque", "session-opaque")] = "CF" + "c" * 32
        adapter = FakeAdapter(ReconciliationResult(ReconciliationState.APPLIED))
        dispatcher = OutboxCommandDispatcher(
            repository=repo, adapters={("twilio", "account-opaque"): adapter},
            worker_id="worker-test",
        )

        dispatcher.dispatch_once()

        self.assertEqual(adapter.reconcile_calls[0][1], "CF" + "c" * 32)

    def test_missing_adapter_defers_without_provider_call(self):
        command = leased_command()
        repo = FakeRepository([command])
        dispatcher = OutboxCommandDispatcher(
            repository=repo, adapters={}, worker_id="worker-test",
        )

        results = dispatcher.dispatch_once()

        self.assertEqual(results[0].outcome, "deferred")
        self.assertEqual(repo.failed[0][2], "provider_adapter_unavailable")
        self.assertEqual(repo.acked, [])

    def test_provider_errors_use_sanitized_codes_and_retry_classification(self):
        command = leased_command()

        class FailingAdapter:
            def reconcile(self, command, *, conference_sid, call_sid):
                raise ProviderOperationError("provider_rate_limited", retryable=True)

            def execute(self, command, *, conference_sid, call_sid):
                raise AssertionError("execute must not run after reconciliation failure")

        repo = FakeRepository([command])
        dispatcher = OutboxCommandDispatcher(
            repository=repo, adapters={("twilio", "account-opaque"): FailingAdapter()},
            worker_id="worker-test", retry_delay_seconds=7,
        )

        results = dispatcher.dispatch_once()

        self.assertEqual(results[0].outcome, "deferred")
        self.assertEqual(repo.failed[0][2:], ("provider_rate_limited", 7))


if __name__ == "__main__":
    unittest.main()
