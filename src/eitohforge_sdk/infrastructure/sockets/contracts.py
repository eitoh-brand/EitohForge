"""Socket infrastructure contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class SocketPrincipal:
    """Authenticated socket principal details."""

    actor_id: str
    tenant_id: str | None = None
    claims: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SocketEnvelope:
    """Outbound socket payload envelope."""

    event: str
    room: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class SocketConnection(Protocol):
    """Socket connection contract."""

    async def send_json(self, payload: Mapping[str, Any]) -> None:
        ...

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        ...


class SocketHub(Protocol):
    """Room membership and broadcast surface used by the realtime WebSocket router."""

    def register(self, connection: SocketConnection, principal: SocketPrincipal) -> str: ...

    def disconnect(self, connection_id: str) -> bool: ...

    def join_room(self, room: str, connection_id: str) -> bool: ...

    def leave_room(self, room: str, connection_id: str) -> bool: ...

    def room_members(self, room: str) -> tuple[str, ...]: ...

    def room_presence(self, room: str) -> dict[str, tuple[str, ...]]: ...

    def connection_rooms(self, connection_id: str) -> tuple[str, ...]:
        """Rooms the connection has joined (normalized room names)."""
        ...

    def principal_for_connection(self, connection_id: str) -> SocketPrincipal | None:
        """Resolved principal for a connection id, if still connected."""
        ...

    async def broadcast(
        self,
        *,
        room: str,
        event: str,
        payload: dict[str, Any] | None = None,
        exclude_connection_id: str | None = None,
    ) -> int: ...

    async def send_direct_to_actor(
        self,
        *,
        target_actor_id: str,
        event: str,
        payload: dict[str, Any] | None = None,
        from_actor_id: str,
        exclude_connection_id: str | None = None,
    ) -> int: ...
