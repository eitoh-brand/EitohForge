"""In-memory room and presence socket hub."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from inspect import isawaitable
from typing import Any

from eitohforge_sdk.infrastructure.sockets.contracts import (
    SocketConnection,
    SocketEnvelope,
    SocketPrincipal,
)


@dataclass
class InMemorySocketHub:
    """In-memory realtime hub with room membership and presence."""

    _connections: dict[str, SocketConnection] = field(default_factory=dict)
    _principals: dict[str, SocketPrincipal] = field(default_factory=dict)
    _rooms: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    _member_rooms: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    _next_connection_id: int = 1

    def register(self, connection: SocketConnection, principal: SocketPrincipal) -> str:
        connection_id = f"conn-{self._next_connection_id}"
        self._next_connection_id += 1
        self._connections[connection_id] = connection
        self._principals[connection_id] = principal
        return connection_id

    def disconnect(self, connection_id: str) -> bool:
        existed = connection_id in self._connections
        self._connections.pop(connection_id, None)
        self._principals.pop(connection_id, None)
        for room in tuple(self._member_rooms.get(connection_id, set())):
            self.leave_room(room, connection_id)
        self._member_rooms.pop(connection_id, None)
        return existed

    def join_room(self, room: str, connection_id: str) -> bool:
        if connection_id not in self._connections:
            return False
        normalized_room = room.strip()
        if not normalized_room:
            return False
        self._rooms[normalized_room].add(connection_id)
        self._member_rooms[connection_id].add(normalized_room)
        return True

    def leave_room(self, room: str, connection_id: str) -> bool:
        normalized_room = room.strip()
        if not normalized_room:
            return False
        members = self._rooms.get(normalized_room)
        if members is None or connection_id not in members:
            return False
        members.discard(connection_id)
        if not members:
            self._rooms.pop(normalized_room, None)
        member_rooms = self._member_rooms.get(connection_id)
        if member_rooms is not None:
            member_rooms.discard(normalized_room)
            if not member_rooms:
                self._member_rooms.pop(connection_id, None)
        return True

    def room_members(self, room: str) -> tuple[str, ...]:
        return tuple(sorted(self._rooms.get(room, set())))

    def room_presence(self, room: str) -> dict[str, tuple[str, ...]]:
        members = self._rooms.get(room, set())
        grouped: dict[str, list[str]] = defaultdict(list)
        for connection_id in members:
            principal = self._principals.get(connection_id)
            if principal is None:
                continue
            grouped[principal.actor_id].append(connection_id)
        return {actor_id: tuple(sorted(connection_ids)) for actor_id, connection_ids in grouped.items()}

    def connection_rooms(self, connection_id: str) -> tuple[str, ...]:
        return tuple(sorted(self._member_rooms.get(connection_id, set())))

    def principal_for_connection(self, connection_id: str) -> SocketPrincipal | None:
        return self._principals.get(connection_id)

    async def broadcast(
        self,
        *,
        room: str,
        event: str,
        payload: dict[str, Any] | None = None,
        exclude_connection_id: str | None = None,
    ) -> int:
        message = SocketEnvelope(event=event, room=room, payload=payload or {})
        delivered = 0
        for connection_id in self._rooms.get(room, set()):
            if exclude_connection_id is not None and connection_id == exclude_connection_id:
                continue
            connection = self._connections.get(connection_id)
            if connection is None:
                continue
            maybe_awaitable = connection.send_json(
                {
                    "event": message.event,
                    "room": message.room,
                    "payload": dict(message.payload),
                    "occurred_at": message.occurred_at.isoformat(),
                }
            )
            if isawaitable(maybe_awaitable):
                await maybe_awaitable
            delivered += 1
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
        """Deliver to all connections whose principal matches ``target_actor_id`` (this process only)."""
        occurred_at = datetime.now(UTC).isoformat()
        body = {
            "event": event,
            "room": "__direct__",
            "payload": dict(payload or {}),
            "occurred_at": occurred_at,
            "from_actor_id": from_actor_id,
            "target_actor_id": target_actor_id,
        }
        delivered = 0
        for connection_id, principal in self._principals.items():
            if principal.actor_id != target_actor_id:
                continue
            if exclude_connection_id is not None and connection_id == exclude_connection_id:
                continue
            connection = self._connections.get(connection_id)
            if connection is None:
                continue
            maybe_awaitable = connection.send_json(body)
            if isawaitable(maybe_awaitable):
                await maybe_awaitable
            delivered += 1
        return delivered
