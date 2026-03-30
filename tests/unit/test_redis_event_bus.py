from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from eitohforge_sdk.infrastructure.messaging.contracts import EventEnvelope
from eitohforge_sdk.infrastructure.messaging.dispatcher import InMemoryEventBus
from eitohforge_sdk.infrastructure.messaging.redis_bridge import RedisPublishingEventBus


def test_redis_publishing_event_bus_notifies_local_and_redis() -> None:
    local = InMemoryEventBus()
    mock_redis = MagicMock()
    mock_redis.publish = AsyncMock(return_value=1)
    bus = RedisPublishingEventBus(_local=local, _redis=mock_redis, _channel_prefix="test:evt:")

    seen: list[str] = []

    async def handler(event: EventEnvelope) -> None:
        seen.append(event.name)

    bus.subscribe("order.created", handler)
    env = EventEnvelope(name="order.created", payload={"id": "ord-1"})

    asyncio.run(bus.publish(env))

    assert seen == ["order.created"]
    mock_redis.publish.assert_awaited_once()
    call_kw = mock_redis.publish.await_args
    assert call_kw[0][0] == "test:evt:order.created"
    assert "ord-1" in call_kw[0][1]
