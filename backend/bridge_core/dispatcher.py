"""Lease-based provider command dispatch with reconciliation before retries.

This module deliberately contains no HTTP client or provider credentials. Concrete
adapters must implement provider-native reconciliation and execute calls outside
database transactions. The dispatcher never blindly retries an uncertain side effect.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping, Protocol

from .persistence import LeasedCommand


class ReconciliationState(StrEnum):
    APPLIED = "applied"
    NOT_APPLIED = "not_applied"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    state: ReconciliationState
    conference_sid: str | None = None
    call_sid: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderExecutionResult:
    conference_sid: str | None = None
    call_sid: str | None = None


class ProviderOperationError(RuntimeError):
    """Sanitized provider failure; message text must never contain request data."""

    def __init__(self, error_code: str, *, retryable: bool):
        if not error_code or len(error_code) > 64:
            raise ValueError("error_code must be a short stable identifier")
        if any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_.-" for ch in error_code):
            raise ValueError("error_code must be a stable identifier")
        self.error_code = error_code
        self.retryable = retryable
        super().__init__(error_code)


class ProviderCommandAdapter(Protocol):
    """A configured provider/account adapter; credentials remain inside the adapter."""

    def reconcile(self, command: LeasedCommand, *, conference_sid: str | None,
                  call_sid: str | None) -> ReconciliationResult: ...

    def execute(self, command: LeasedCommand, *, conference_sid: str | None,
                call_sid: str | None) -> ProviderExecutionResult: ...


class DispatchRepository(Protocol):
    def claim_outbox(self, *, worker_id: str, limit: int = 10,
                     lease_seconds: int = 30) -> tuple[LeasedCommand, ...]: ...

    def acknowledge_outbox(self, command_id, lease_token) -> None: ...

    def fail_outbox(self, command_id, lease_token, *, error_code: str,
                    retry_delay_seconds: int) -> str: ...

    def get_provider_resource(self, provider: str, provider_account_id: str,
                              session_id: str) -> str | None: ...

    def put_provider_resource(self, provider: str, provider_account_id: str,
                              session_id: str, conference_sid: str) -> None: ...

    def get_provider_participant_resource(self, provider: str, provider_account_id: str,
                                          session_id: str, participant_ref: str) -> str | None: ...

    def put_provider_participant_resource(self, provider: str, provider_account_id: str,
                                          session_id: str, participant_ref: str,
                                          call_sid: str) -> None: ...


@dataclass(frozen=True, slots=True)
class DispatchResult:
    command_id: str
    outcome: str


class OutboxCommandDispatcher:
    """Dispatch a claimed batch; every retry starts with provider reconciliation."""

    def __init__(self, *, repository: DispatchRepository,
                 adapters: Mapping[tuple[str, str], ProviderCommandAdapter],
                 worker_id: str, lease_seconds: int = 60,
                 retry_delay_seconds: int = 5):
        if not worker_id.strip():
            raise ValueError("worker_id must not be empty")
        if not 1 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds must be between 1 and 3600")
        if not 0 <= retry_delay_seconds <= 86400:
            raise ValueError("retry_delay_seconds must be between 0 and 86400")
        self._repository = repository
        self._adapters = dict(adapters)
        self._worker_id = worker_id
        self._lease_seconds = lease_seconds
        self._retry_delay_seconds = retry_delay_seconds

    def dispatch_once(self, *, limit: int = 10) -> tuple[DispatchResult, ...]:
        commands = self._repository.claim_outbox(
            worker_id=self._worker_id, limit=limit,
            lease_seconds=self._lease_seconds,
        )
        return tuple(self._dispatch(command) for command in commands)

    def _dispatch(self, command: LeasedCommand) -> DispatchResult:
        key = (command.provider, command.provider_account_id)
        adapter = self._adapters.get(key)
        if adapter is None:
            self._repository.fail_outbox(
                command.command_id, command.lease_token,
                error_code="provider_adapter_unavailable",
                retry_delay_seconds=86400,
            )
            return DispatchResult(str(command.command_id), "deferred")

        try:
            # Provider I/O occurs after the outbox lease transaction has committed.
            # If the mapping is absent (crash after remote create), the adapter must
            # reconcile using the stable command correlation key before creating again.
            conference_sid = self._repository.get_provider_resource(
                command.provider, command.provider_account_id, command.session_id,
            )
            participant_ref = command.payload.get("participant_ref")
            call_sid = None
            if isinstance(participant_ref, str):
                call_sid = self._repository.get_provider_participant_resource(
                    command.provider, command.provider_account_id,
                    command.session_id, participant_ref,
                )
            reconciliation = adapter.reconcile(
                command, conference_sid=conference_sid, call_sid=call_sid,
            )
            if reconciliation.state is ReconciliationState.UNKNOWN:
                self._repository.fail_outbox(
                    command.command_id, command.lease_token,
                    error_code="provider_outcome_unknown",
                    retry_delay_seconds=self._retry_delay_seconds,
                )
                return DispatchResult(str(command.command_id), "reconciliation_required")

            if reconciliation.state is ReconciliationState.NOT_APPLIED:
                execution = adapter.execute(
                    command, conference_sid=conference_sid, call_sid=call_sid,
                )
                conference_sid = execution.conference_sid or conference_sid
                call_sid = execution.call_sid or call_sid
            else:
                conference_sid = reconciliation.conference_sid or conference_sid
                call_sid = reconciliation.call_sid or call_sid

            if command.command_type == "conference.create" and not conference_sid:
                raise ProviderOperationError("provider_conference_sid_missing", retryable=True)
            if command.command_type == "participant.add" and (not isinstance(participant_ref, str) or not call_sid):
                raise ProviderOperationError("provider_participant_sid_missing", retryable=True)
            if conference_sid:
                self._repository.put_provider_resource(
                    command.provider, command.provider_account_id,
                    command.session_id, conference_sid,
                )
            if call_sid and isinstance(participant_ref, str):
                self._repository.put_provider_participant_resource(
                    command.provider, command.provider_account_id,
                    command.session_id, participant_ref, call_sid,
                )
            self._repository.acknowledge_outbox(command.command_id, command.lease_token)
            return DispatchResult(str(command.command_id), "acknowledged")

        except ProviderOperationError as exc:
            delay = self._retry_delay_seconds if exc.retryable else 86400
            self._repository.fail_outbox(
                command.command_id, command.lease_token,
                error_code=exc.error_code, retry_delay_seconds=delay,
            )
            return DispatchResult(str(command.command_id), "deferred")
        except Exception:
            # Do not leak exception text (which may contain provider request data).
            # Best-effort release prevents one malformed adapter result from blocking
            # the rest of the claimed batch until lease expiry.
            self._repository.fail_outbox(
                command.command_id, command.lease_token,
                error_code="dispatcher_internal_error",
                retry_delay_seconds=self._retry_delay_seconds,
            )
            return DispatchResult(str(command.command_id), "deferred")
