"""Saga orchestration scaffold for distributed transaction workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol
from uuid import uuid4


class SagaStatus(str, Enum):
    """Saga execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    COMPENSATED = "compensated"


@dataclass
class SagaContext:
    """Shared mutable context passed across saga steps."""

    saga_id: str = field(default_factory=lambda: str(uuid4()))
    trace_id: str | None = None
    tenant_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


class SagaStep(Protocol):
    """Saga step contract with execute and compensate hooks."""

    name: str

    async def execute(self, context: SagaContext) -> None:
        """Execute forward operation."""

    async def compensate(self, context: SagaContext) -> None:
        """Compensate reverse operation."""


class SagaStateStore(Protocol):
    """Persistence contract for saga execution states."""

    def start(self, saga_name: str, context: SagaContext) -> None:
        """Persist saga start state."""

    def step_executed(self, saga_name: str, context: SagaContext, step_name: str) -> None:
        """Persist successful step execution."""

    def step_compensated(self, saga_name: str, context: SagaContext, step_name: str) -> None:
        """Persist compensated step event."""

    def finish(self, saga_name: str, context: SagaContext, status: SagaStatus) -> None:
        """Persist terminal saga status."""


@dataclass
class InMemorySagaStateStore:
    """In-memory saga state store for baseline orchestration."""

    events: list[tuple[str, str, str, str]] = field(default_factory=list)

    def start(self, saga_name: str, context: SagaContext) -> None:
        self.events.append((saga_name, context.saga_id, "start", SagaStatus.RUNNING.value))

    def step_executed(self, saga_name: str, context: SagaContext, step_name: str) -> None:
        self.events.append((saga_name, context.saga_id, "step", f"executed:{step_name}"))

    def step_compensated(self, saga_name: str, context: SagaContext, step_name: str) -> None:
        self.events.append((saga_name, context.saga_id, "step", f"compensated:{step_name}"))

    def finish(self, saga_name: str, context: SagaContext, status: SagaStatus) -> None:
        self.events.append((saga_name, context.saga_id, "finish", status.value))


@dataclass(frozen=True)
class SagaExecutionResult:
    """Result object for saga orchestration outcomes."""

    status: SagaStatus
    executed_steps: tuple[str, ...]
    compensated_steps: tuple[str, ...]
    error_message: str | None = None


class SagaOrchestrator:
    """Sequential saga orchestrator with compensation support."""

    def __init__(self, state_store: SagaStateStore | None = None) -> None:
        self._state_store = state_store or InMemorySagaStateStore()

    async def run(
        self, saga_name: str, steps: tuple[SagaStep, ...], context: SagaContext | None = None
    ) -> SagaExecutionResult:
        """Run saga steps; compensate in reverse order on failure."""
        saga_context = context or SagaContext()
        executed_steps: list[SagaStep] = []
        compensated_names: list[str] = []
        self._state_store.start(saga_name, saga_context)

        try:
            for step in steps:
                await step.execute(saga_context)
                executed_steps.append(step)
                self._state_store.step_executed(saga_name, saga_context, step.name)

            self._state_store.finish(saga_name, saga_context, SagaStatus.SUCCEEDED)
            return SagaExecutionResult(
                status=SagaStatus.SUCCEEDED,
                executed_steps=tuple(step.name for step in executed_steps),
                compensated_steps=(),
            )
        except Exception as exc:
            for step in reversed(executed_steps):
                try:
                    await step.compensate(saga_context)
                    compensated_names.append(step.name)
                    self._state_store.step_compensated(saga_name, saga_context, step.name)
                except Exception:
                    # Compensation failures are recorded by omission.
                    continue
            final_status = SagaStatus.COMPENSATED if compensated_names else SagaStatus.FAILED
            self._state_store.finish(saga_name, saga_context, final_status)
            return SagaExecutionResult(
                status=final_status,
                executed_steps=tuple(step.name for step in executed_steps),
                compensated_steps=tuple(compensated_names),
                error_message=str(exc),
            )

