"""Room presence: status metadata, snapshots, and broadcast events on top of :class:`SocketHub`."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from eitohforge_sdk.infrastructure.sockets.contracts import SocketHub


class PresenceStatus(str, Enum):
    """Coarse presence state for a connection."""

    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"


# Wire protocol event names (stable for clients).
PRESENCE_EVENT_JOIN = "presence:join"
PRESENCE_EVENT_LEAVE = "presence:leave"
PRESENCE_EVENT_UPDATE = "presence:update"


@dataclass(frozen=True)
class ActorPresence:
    """Aggregated presence for one actor within a room."""

    actor_id: str
    tenant_id: str | None
    connection_count: int
    status: PresenceStatus
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RoomPresenceSnapshot:
    """Immutable view of who is in a room."""

    room: str
    actors: tuple[ActorPresence, ...]


def _merge_status(statuses: list[PresenceStatus]) -> PresenceStatus:
    if PresenceStatus.BUSY in statuses:
        return PresenceStatus.BUSY
    if PresenceStatus.AWAY in statuses:
        return PresenceStatus.AWAY
    return PresenceStatus.ONLINE


def _merge_metadata(
    connection_ids: tuple[str, ...],
    meta: Mapping[str, Any],
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for cid in sorted(connection_ids):
        m = meta.get(cid)
        if isinstance(m, Mapping):
            merged.update(dict(m))
    return merged


class PresenceManager:
    """Track per-connection presence status and emit presence events via the hub."""

    def __init__(self, hub: SocketHub) -> None:
        self._hub = hub
        self._status: dict[str, PresenceStatus] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def snapshot(self, room: str) -> RoomPresenceSnapshot:
        """Build a structured presence view for ``room`` (hub membership + local status)."""
        normalized = room.strip()
        by_actor = self._hub.room_presence(normalized)
        actors: list[ActorPresence] = []
        for actor_id in sorted(by_actor.keys()):
            cids = by_actor[actor_id]
            st = _merge_status([self._status.get(cid, PresenceStatus.ONLINE) for cid in cids])
            principal = self._hub.principal_for_connection(cids[0])
            tenant_id = principal.tenant_id if principal is not None else None
            meta = _merge_metadata(cids, self._metadata)
            actors.append(
                ActorPresence(
                    actor_id=actor_id,
                    tenant_id=tenant_id,
                    connection_count=len(cids),
                    status=st,
                    metadata=meta,
                )
            )
        return RoomPresenceSnapshot(room=normalized, actors=tuple(actors))

    async def join(
        self,
        room: str,
        connection_id: str,
        *,
        status: PresenceStatus = PresenceStatus.ONLINE,
        metadata: Mapping[str, Any] | None = None,
        broadcast_event: bool = True,
    ) -> bool:
        """Join a room, set presence for this connection, optionally broadcast ``presence:join``."""
        ok = self._hub.join_room(room, connection_id)
        if not ok:
            return False
        self._status[connection_id] = status
        if metadata is not None:
            if metadata:
                self._metadata[connection_id] = dict(metadata)
            else:
                self._metadata.pop(connection_id, None)
        if broadcast_event:
            principal = self._hub.principal_for_connection(connection_id)
            actor_id = principal.actor_id if principal is not None else "unknown"
            payload = {
                "room": room.strip(),
                "connection_id": connection_id,
                "actor_id": actor_id,
                "status": status.value,
                "metadata": dict(self._metadata.get(connection_id, {})),
            }
            await self._hub.broadcast(
                room=room.strip(),
                event=PRESENCE_EVENT_JOIN,
                payload=payload,
                exclude_connection_id=connection_id,
            )
        return True

    async def leave(
        self,
        room: str,
        connection_id: str,
        *,
        broadcast_event: bool = True,
    ) -> bool:
        """Leave a room, clear local state when no longer in any room, optionally ``presence:leave``."""
        principal = self._hub.principal_for_connection(connection_id)
        actor_id = principal.actor_id if principal is not None else "unknown"
        ok = self._hub.leave_room(room, connection_id)
        if not ok:
            return False
        if broadcast_event:
            await self._hub.broadcast(
                room=room.strip(),
                event=PRESENCE_EVENT_LEAVE,
                payload={
                    "room": room.strip(),
                    "connection_id": connection_id,
                    "actor_id": actor_id,
                },
                exclude_connection_id=connection_id,
            )
        if not self._hub.connection_rooms(connection_id):
            self._status.pop(connection_id, None)
            self._metadata.pop(connection_id, None)
        return True

    async def update_status(
        self,
        connection_id: str,
        status: PresenceStatus,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """Update presence for a connection and notify all rooms it belongs to."""
        if self._hub.principal_for_connection(connection_id) is None:
            return
        self._status[connection_id] = status
        if metadata is not None:
            if metadata:
                self._metadata[connection_id] = dict(metadata)
            else:
                self._metadata.pop(connection_id, None)
        principal = self._hub.principal_for_connection(connection_id)
        actor_id = principal.actor_id if principal is not None else "unknown"
        for room in self._hub.connection_rooms(connection_id):
            await self._hub.broadcast(
                room=room,
                event=PRESENCE_EVENT_UPDATE,
                payload={
                    "room": room,
                    "connection_id": connection_id,
                    "actor_id": actor_id,
                    "status": status.value,
                    "metadata": dict(self._metadata.get(connection_id, {})),
                },
                exclude_connection_id=connection_id,
            )

    def disconnect(self, connection_id: str) -> bool:
        """Disconnect from the hub and drop local presence state."""
        self._status.pop(connection_id, None)
        self._metadata.pop(connection_id, None)
        return self._hub.disconnect(connection_id)

    def clear_local_state(self, connection_id: str) -> None:
        """Drop presence metadata if the hub was disconnected without using :meth:`disconnect`."""
        self._status.pop(connection_id, None)
        self._metadata.pop(connection_id, None)
