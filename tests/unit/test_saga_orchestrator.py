from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from eitohforge_sdk.infrastructure.transactions.saga import (
    InMemorySagaStateStore,
    SagaContext,
    SagaOrchestrator,
    SagaStatus,
)


@dataclass
class RecordingStep:
    name: str
    fail_on_execute: bool = False
    order: list[str] = field(default_factory=list)

    async def execute(self, context: SagaContext) -> None:
        _ = context
        self.order.append(f"execute:{self.name}")
        if self.fail_on_execute:
            raise RuntimeError(f"failed:{self.name}")

    async def compensate(self, context: SagaContext) -> None:
        _ = context
        self.order.append(f"compensate:{self.name}")


def test_saga_orchestrator_success_path() -> None:
    store = InMemorySagaStateStore()
    orchestrator = SagaOrchestrator(state_store=store)
    step_a = RecordingStep(name="a")
    step_b = RecordingStep(name="b")

    result = asyncio.run(orchestrator.run("signup", (step_a, step_b)))
    assert result.status == SagaStatus.SUCCEEDED
    assert result.executed_steps == ("a", "b")
    assert result.compensated_steps == ()
    assert ("signup", store.events[0][1], "finish", "succeeded") in store.events


def test_saga_orchestrator_compensates_reverse_on_failure() -> None:
    store = InMemorySagaStateStore()
    orchestrator = SagaOrchestrator(state_store=store)
    step_a = RecordingStep(name="a")
    step_b = RecordingStep(name="b")
    step_c = RecordingStep(name="c", fail_on_execute=True)

    result = asyncio.run(orchestrator.run("checkout", (step_a, step_b, step_c)))
    assert result.status == SagaStatus.COMPENSATED
    assert result.executed_steps == ("a", "b")
    assert result.compensated_steps == ("b", "a")
    assert any(event[-1] == "compensated:b" for event in store.events)
    assert any(event[-1] == "compensated:a" for event in store.events)

