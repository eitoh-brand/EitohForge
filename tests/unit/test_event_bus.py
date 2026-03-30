from __future__ import annotations

import asyncio

from eitohforge_sdk.infrastructure.messaging import EventEnvelope, InMemoryEventBus


def test_in_memory_event_bus_dispatches_registered_handlers() -> None:
    bus = InMemoryEventBus()
    received: list[tuple[str, object]] = []

    async def on_order_created(event: EventEnvelope) -> None:
        received.append((event.name, event.payload["order_id"]))

    bus.subscribe("order.created", on_order_created)
    asyncio.run(bus.publish(EventEnvelope(name="order.created", payload={"order_id": "ord-1"})))

    assert received == [("order.created", "ord-1")]


def test_in_memory_event_bus_supports_wildcard_handlers() -> None:
    bus = InMemoryEventBus()
    names: list[str] = []

    def on_any_event(event: EventEnvelope) -> None:
        names.append(event.name)

    bus.subscribe("*", on_any_event)
    asyncio.run(
        bus.publish_many(
            (
                EventEnvelope(name="a.happened"),
                EventEnvelope(name="b.happened"),
            )
        )
    )

    assert names == ["a.happened", "b.happened"]

