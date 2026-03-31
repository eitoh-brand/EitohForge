"""Redis-backed broadcast fan-out for multi-worker WebSocket hubs."""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from typing import Any

from eitohforge_sdk.core.config import AppSettings
from eitohforge_sdk.infrastructure.sockets.contracts import SocketConnection, SocketPrincipal
from eitohforge_sdk.infrastructure.sockets.hub import InMemorySocketHub

CLUSTER_BROADCAST_SCHEMA_VERSION = 1
CLUSTER_MESSAGE_KIND_BROADCAST = "broadcast"
CLUSTER_MESSAGE_KIND_DIRECT = "direct"


@dataclass
class RedisFanoutSocketHub:
    """Process-local sockets with cluster-wide **broadcast** via Redis PUBLISH.

    Join/leave and ``presence`` / ``room_members`` remain **local to this worker**. **Broadcast** and
    **direct-to-actor** sends are replicated to peer workers via the same Redis channel.
    """

    _inner: InMemorySocketHub
    _redis_publish: Any
    _channel: str
    _publisher_id: str

    def register(self, connection: SocketConnection, principal: SocketPrincipal) -> str:
        return self._inner.register(connection, principal)

    def disconnect(self, connection_id: str) -> bool:
        return self._inner.disconnect(connection_id)

    def join_room(self, room: str, connection_id: str) -> bool:
        return self._inner.join_room(room, connection_id)

    def leave_room(self, room: str, connection_id: str) -> bool:
        return self._inner.leave_room(room, connection_id)

    def room_members(self, room: str) -> tuple[str, ...]:
        return self._inner.room_members(room)

    def room_presence(self, room: str) -> dict[str, tuple[str, ...]]:
        return self._inner.room_presence(room)

    def connection_rooms(self, connection_id: str) -> tuple[str, ...]:
        return self._inner.connection_rooms(connection_id)

    def principal_for_connection(self, connection_id: str) -> SocketPrincipal | None:
        return self._inner.principal_for_connection(connection_id)

    async def broadcast(
        self,
        *,
        room: str,
        event: str,
        payload: dict[str, Any] | None = None,
        exclude_connection_id: str | None = None,
    ) -> int:
        delivered = await self._inner.broadcast(
            room=room,
            event=event,
            payload=payload,
            exclude_connection_id=exclude_connection_id,
        )
        body = json.dumps(
            {
                "v": CLUSTER_BROADCAST_SCHEMA_VERSION,
                "kind": CLUSTER_MESSAGE_KIND_BROADCAST,
                "publisher_id": self._publisher_id,
                "room": room,
                "event": event,
                "payload": dict(payload or {}),
            },
            default=str,
        )
        await self._redis_publish.publish(self._channel, body)
        return delivered

    async def send_direct_to_actor(
        self,
        *,
        target_actor_id: str,
        event: str,
        payload: dict[str, Any] | None = None,
        from_actor_id: str,
        exclude_connection_id: str | None = None,
    ) -> int:
        delivered = await self._inner.send_direct_to_actor(
            target_actor_id=target_actor_id,
            event=event,
            payload=payload,
            from_actor_id=from_actor_id,
            exclude_connection_id=exclude_connection_id,
        )
        body = json.dumps(
            {
                "v": CLUSTER_BROADCAST_SCHEMA_VERSION,
                "kind": CLUSTER_MESSAGE_KIND_DIRECT,
                "publisher_id": self._publisher_id,
                "target_actor_id": target_actor_id,
                "event": event,
                "payload": dict(payload or {}),
                "from_actor_id": from_actor_id,
            },
            default=str,
        )
        await self._redis_publish.publish(self._channel, body)
        return delivered

    async def deliver_cluster_broadcast(self, *, publisher_id: str, room: str, event: str, payload: dict[str, Any]) -> int:
        """Deliver a message from Redis; skips echo from this worker."""
        if publisher_id == self._publisher_id:
            return 0
        return await self._inner.broadcast(room=room, event=event, payload=payload, exclude_connection_id=None)

    async def deliver_cluster_direct(
        self,
        *,
        publisher_id: str,
        target_actor_id: str,
        event: str,
        payload: dict[str, Any],
        from_actor_id: str,
    ) -> int:
        if publisher_id == self._publisher_id:
            return 0
        return await self._inner.send_direct_to_actor(
            target_actor_id=target_actor_id,
            event=event,
            payload=payload,
            from_actor_id=from_actor_id,
            exclude_connection_id=None,
        )

    async def aclose(self) -> None:
        close = getattr(self._redis_publish, "aclose", None)
        if callable(close):
            result = close()
            if inspect.isawaitable(result):
                await result
            return
        close_sync = getattr(self._redis_publish, "close", None)
        if callable(close_sync):
            maybe = close_sync()
            if inspect.isawaitable(maybe):
                await maybe


def build_socket_hub_for_settings(settings: AppSettings) -> InMemorySocketHub | RedisFanoutSocketHub:
    """Return in-memory hub, or Redis fan-out wrapper when ``RealtimeSettings.redis_url`` is set."""
    inner = InMemorySocketHub()
    url = settings.realtime.redis_url
    if not url:
        return inner
    import uuid

    import redis.asyncio as redis_async

    pub = redis_async.from_url(url, decode_responses=True)
    return RedisFanoutSocketHub(
        _inner=inner,
        _redis_publish=pub,
        _channel=settings.realtime.redis_broadcast_channel,
        _publisher_id=str(uuid.uuid4()),
    )


async def dispatch_redis_fanout_payload(hub: InMemorySocketHub | RedisFanoutSocketHub, raw: str) -> int:
    """Parse a Redis pub/sub payload and deliver locally; no-op for plain in-memory hubs."""
    if not isinstance(hub, RedisFanoutSocketHub):
        return 0
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return 0
    if not isinstance(data, dict):
        return 0
    if data.get("v") != CLUSTER_BROADCAST_SCHEMA_VERSION:
        return 0
    publisher_id = data.get("publisher_id")
    if not isinstance(publisher_id, str):
        return 0
    kind = data.get("kind", CLUSTER_MESSAGE_KIND_BROADCAST)
    if kind == CLUSTER_MESSAGE_KIND_DIRECT:
        target_actor_id = data.get("target_actor_id")
        event = data.get("event")
        from_actor_id = data.get("from_actor_id")
        payload = data.get("payload")
        if (
            not isinstance(target_actor_id, str)
            or not isinstance(event, str)
            or not isinstance(from_actor_id, str)
        ):
            return 0
        if not isinstance(payload, dict):
            payload = {}
        return await hub.deliver_cluster_direct(
            publisher_id=publisher_id,
            target_actor_id=target_actor_id,
            event=event,
            payload=payload,
            from_actor_id=from_actor_id,
        )
    if kind != CLUSTER_MESSAGE_KIND_BROADCAST:
        return 0
    room = data.get("room")
    event = data.get("event")
    payload = data.get("payload")
    if not isinstance(room, str) or not isinstance(event, str):
        return 0
    if not isinstance(payload, dict):
        payload = {}
    return await hub.deliver_cluster_broadcast(
        publisher_id=publisher_id, room=room, event=event, payload=payload
    )
