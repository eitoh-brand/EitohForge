from __future__ import annotations

import asyncio

from eitohforge_sdk.infrastructure.messaging.contracts import EventEnvelope
from eitohforge_sdk.infrastructure.messaging.dispatcher import InMemoryEventBus
from eitohforge_sdk.infrastructure.messaging.domain_events import DomainEvent, DomainEventPublisher


def test_domain_event_to_envelope() -> None:
    ev = DomainEvent(name="order.placed", aggregate_id="o1", payload={"id": "o1"})
    env = ev.to_envelope()
    assert env.name == "order.placed"
    assert env.payload == {"id": "o1"}
    assert env.metadata.get("aggregate_id") == "o1"


def test_domain_event_publisher() -> None:
    bus = InMemoryEventBus()
    seen: list[EventEnvelope] = []

    async def h(e: EventEnvelope) -> None:
        seen.append(e)

    bus.subscribe("order.placed", h)
    pub = DomainEventPublisher(bus)

    async def _run() -> None:
        await pub.publish(DomainEvent(name="order.placed", payload={"x": 1}))

    asyncio.run(_run())
    assert len(seen) == 1
    assert seen[0].name == "order.placed"
