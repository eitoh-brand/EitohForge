"""Redis-backed publish sidecar for the in-process event bus (cross-worker fan-out)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from eitohforge_sdk.infrastructure.messaging.contracts import EventEnvelope, EventHandler
from eitohforge_sdk.infrastructure.messaging.dispatcher import InMemoryEventBus


@dataclass
class RedisPublishingEventBus:
    """Dispatches to local ``InMemoryEventBus`` handlers and ``PUBLISH``es JSON to Redis.

    Subscribers on other processes must run their own Redis ``SUBSCRIBE`` loop; this class
    does not start a listener (see cookbook).
    """

    _local: InMemoryEventBus
    _redis: Any
    _channel_prefix: str = "eitohforge:evt:"

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._local.subscribe(event_name, handler)

    async def publish(self, event: EventEnvelope) -> None:
        await self._local.publish(event)
        body = json.dumps(
            {
                "name": event.name,
                "payload": dict(event.payload),
                "metadata": dict(event.metadata),
                "occurred_at": event.occurred_at.isoformat(),
            },
            default=str,
        )
        await self._redis.publish(f"{self._channel_prefix}{event.name}", body)


def build_redis_publishing_event_bus(
    *, redis_url: str, channel_prefix: str = "eitohforge:evt:"
) -> RedisPublishingEventBus:
    """Build a bus with a fresh in-memory handler registry and async Redis client."""
    import redis.asyncio as redis_async

    client = redis_async.from_url(redis_url, decode_responses=True)
    return RedisPublishingEventBus(_local=InMemoryEventBus(), _redis=client, _channel_prefix=channel_prefix)
