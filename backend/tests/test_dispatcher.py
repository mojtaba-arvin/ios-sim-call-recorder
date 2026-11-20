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
        self.consent_resources = {}
        self.acked = []
        self.failed = []
        self.terminals = []

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

    def get_provider_consent_call_resource(self, provider, account, session, participant_ref):
        return self.consent_resources.get((provider, account, session, participant_ref))

    def put_provider_consent_call_resource(self, provider, account, session, participant_ref, call_sid):
        key = (provider, account, session, participant_ref)
        existing = self.consent_resources.get(key)
        if existing is not None and existing != call_sid:
            raise AssertionError("consent call mapping must be immutable")
        self.consent_resources[key] = call_sid

    def put_provider_participant_resource(self, provider, account, session, participant_ref, call_sid):
        key = (provider, account, session, participant_ref)
        existing = self.participant_resources.get(key)
        if existing is not None and existing != call_sid:
            raise AssertionError("participant mapping must be immutable")
        self.participant_resources[key] = call_sid

    def acknowledge_outbox(self, command_id, lease_token):
        self.acked.append((command_id, lease_token))

    def fail_outbox(self, command_id, lease_token, *, error_code, retry_delay_seconds, terminal=False):
        self.failed.append((command_id, lease_token, error_code, retry_delay_seconds))
        self.terminals.append(terminal)
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


_DEFAULT_PARTICIPANT = object()


def leased_command(*, participant_ref=_DEFAULT_PARTICIPANT, command_type="recording.start"):
    payload = {"session_id": "session-opaque"}
    if participant_ref is _DEFAULT_PARTICIPANT:
        participant_ref = (
            "participant-opaque-1"
            if command_type in {"conference.create", "participant.add"}
            else None
        )
    if participant_ref is not None:
        payload["participant_ref"] = participant_ref
    if command_type == "conference.create":
        payload["recording_mode"] = "from_start"
    return LeasedCommand(
        command_id=uuid4(),
        command_type=command_type,
        idempotency_key="recording-start:twilio:account-opaque:session-opaque",
        session_id="session-opaque",
        provider="twilio",
        provider_account_id="account-opaque",
        payload=payload,
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

    def test_participant_call_sid_is_reconciled_and_persisted_by_opaque_reference(self):
        command = leased_command(participant_ref="participant-opaque-1", command_type="participant.add")
        repo = FakeRepository([command])
        repo.resources[("twilio", "account-opaque", "session-opaque")] = "CF" + "d" * 32
        adapter = FakeAdapter(
            ReconciliationResult(ReconciliationState.APPLIED, call_sid="CA" + "e" * 32),
        )
        dispatcher = OutboxCommandDispatcher(
            repository=repo, adapters={("twilio", "account-opaque"): adapter},
            worker_id="worker-test",
        )

        dispatcher.dispatch_once()

        self.assertEqual(adapter.reconcile_calls[0][2], None)
        self.assertEqual(
            repo.participant_resources[("twilio", "account-opaque", "session-opaque",
                                        "participant-opaque-1")],
            "CA" + "e" * 32,
        )

    def test_consent_call_sid_is_stored_separately_from_conference_leg(self):
        command = leased_command(participant_ref="participant-opaque-1", command_type="consent.request")
        repo = FakeRepository([command])
        adapter = FakeAdapter(
            ReconciliationResult(ReconciliationState.NOT_APPLIED),
            ProviderExecutionResult(call_sid="CA" + "f" * 32),
        )
        dispatcher = OutboxCommandDispatcher(
            repository=repo, adapters={("twilio", "account-opaque"): adapter},
            worker_id="worker-test",
        )
        result = dispatcher.dispatch_once()
        self.assertEqual(result[0].outcome, "acknowledged")
        key = ("twilio", "account-opaque", "session-opaque", "participant-opaque-1")
        self.assertEqual(repo.consent_resources[key], "CA" + "f" * 32)
        self.assertNotIn(key, repo.participant_resources)

    def test_malformed_reconciliation_state_is_never_treated_as_applied(self):
        command = leased_command()

        class MalformedAdapter:
            def reconcile(self, command, *, conference_sid, call_sid):
                return ReconciliationResult(
                    "applied",
                    conference_sid="CF" + "a" * 32,
                )

            def execute(self, command, *, conference_sid, call_sid):
                raise AssertionError("malformed reconciliation must not execute")

        repo = FakeRepository([command])
        adapter = MalformedAdapter()
        dispatcher = OutboxCommandDispatcher(
            repository=repo,
            adapters={("twilio", "account-opaque"): adapter},
            worker_id="worker-test",
        )

        results = dispatcher.dispatch_once()

        self.assertEqual(results[0].outcome, "deferred")
        self.assertEqual(repo.acked, [])
        self.assertEqual(repo.failed[0][2], "provider_reconciliation_invalid")
        self.assertFalse(repo.terminals[0])

    def test_invalid_participant_reference_is_dead_lettered_before_provider_io(self):
        invalid_references = (None, "", "   ", "participant ref", "x" * 129)
        for participant_ref in invalid_references:
            with self.subTest(participant_ref=participant_ref):
                command = leased_command(
                    participant_ref=participant_ref,
                    command_type="participant.add",
                )
                repo = FakeRepository([command])
                adapter = FakeAdapter(
                    ReconciliationResult(ReconciliationState.NOT_APPLIED),
                    ProviderExecutionResult(call_sid="CA" + "f" * 32),
                )
                dispatcher = OutboxCommandDispatcher(
                    repository=repo,
                    adapters={("twilio", "account-opaque"): adapter},
                    worker_id="worker-test",
                )

                results = dispatcher.dispatch_once()

                self.assertEqual(results[0].outcome, "deferred")
                self.assertEqual(adapter.reconcile_calls, [])
                self.assertEqual(adapter.execute_calls, [])
                self.assertEqual(repo.failed[0][2], "participant_reference_invalid")
                self.assertTrue(repo.terminals[0])

    def test_create_command_without_provider_resource_is_not_acknowledged(self):
        command = leased_command(command_type="conference.create")
        repo = FakeRepository([command])
        adapter = FakeAdapter(ReconciliationResult(ReconciliationState.NOT_APPLIED))
        dispatcher = OutboxCommandDispatcher(
            repository=repo, adapters={("twilio", "account-opaque"): adapter},
            worker_id="worker-test",
        )

        results = dispatcher.dispatch_once()

        self.assertEqual(results[0].outcome, "deferred")
        self.assertEqual(repo.acked, [])
        self.assertEqual(repo.failed[0][2], "provider_conference_or_participant_sid_missing")


    def test_conference_create_requires_recording_from_start_and_both_resource_ids(self):
        command = leased_command(command_type="conference.create")
        repo = FakeRepository([command])
        adapter = FakeAdapter(
            ReconciliationResult(ReconciliationState.NOT_APPLIED),
            ProviderExecutionResult(
                conference_sid="CF" + "a" * 32,
                call_sid="CA" + "b" * 32,
            ),
        )
        dispatcher = OutboxCommandDispatcher(
            repository=repo,
            adapters={("twilio", "account-opaque"): adapter},
            worker_id="worker-test",
        )
        result = dispatcher.dispatch_once()[0]
        self.assertEqual(result.outcome, "acknowledged")
        self.assertEqual(
            repo.participant_resources[("twilio", "account-opaque", "session-opaque",
                                        "participant-opaque-1")],
            "CA" + "b" * 32,
        )

    def test_conference_create_rejects_unsupported_recording_mode_before_provider_io(self):
        command = leased_command(command_type="conference.create")
        command = command.__class__(
            command_id=command.command_id,
            command_type=command.command_type,
            idempotency_key=command.idempotency_key,
            session_id=command.session_id,
            provider=command.provider,
            provider_account_id=command.provider_account_id,
            payload={"session_id": command.session_id,
                     "participant_ref": "participant-opaque-1",
                     "recording_mode": "after_join"},
            attempts=command.attempts,
            lease_token=command.lease_token,
            lease_owner=command.lease_owner,
            lease_expires_at=command.lease_expires_at,
        )
        repo = FakeRepository([command])
        adapter = FakeAdapter(ReconciliationResult(ReconciliationState.NOT_APPLIED))
        dispatcher = OutboxCommandDispatcher(
            repository=repo,
            adapters={("twilio", "account-opaque"): adapter},
            worker_id="worker-test",
        )
        result = dispatcher.dispatch_once()[0]
        self.assertEqual(result.outcome, "deferred")
        self.assertEqual(adapter.reconcile_calls, [])
        self.assertEqual(repo.failed[0][2], "conference_recording_mode_invalid")
        self.assertTrue(repo.terminals[0])

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

    def test_permanent_provider_error_is_dead_lettered_without_retry(self):
        command = leased_command()

        class PermanentFailureAdapter:
            def reconcile(self, command, *, conference_sid, call_sid):
                raise ProviderOperationError("provider_request_rejected", retryable=False)

            def execute(self, command, *, conference_sid, call_sid):
                raise AssertionError("execute must not run after permanent reconciliation failure")

        repo = FakeRepository([command])
        dispatcher = OutboxCommandDispatcher(
            repository=repo, adapters={("twilio", "account-opaque"): PermanentFailureAdapter()},
            worker_id="worker-test",
        )

        results = dispatcher.dispatch_once()

        self.assertEqual(results[0].outcome, "deferred")
        self.assertEqual(repo.failed[0][2], "provider_request_rejected")
        self.assertTrue(repo.terminals[0])

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
