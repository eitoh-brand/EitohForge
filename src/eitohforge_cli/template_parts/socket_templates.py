"""Socket infrastructure template fragments."""

SOCKET_FILE_TEMPLATES: dict[str, str] = {
    "app/infrastructure/sockets/__init__.py": """from app.infrastructure.sockets.auth import (
    JwtSocketAuthenticator,
    SocketAuthenticationError,
    extract_socket_token,
)
from app.infrastructure.sockets.contracts import SocketConnection, SocketEnvelope, SocketPrincipal
from app.infrastructure.sockets.hub import InMemorySocketHub
""",
    "app/infrastructure/sockets/contracts.py": """from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class SocketPrincipal:
    actor_id: str
    tenant_id: str | None = None
    claims: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SocketEnvelope:
    event: str
    room: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class SocketConnection(Protocol):
    async def send_json(self, payload: Mapping[str, Any]) -> None:
        ...

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        ...
""",
    "app/infrastructure/sockets/auth.py": """from collections.abc import Mapping
from dataclasses import dataclass

from app.core.auth import JwtTokenManager, TokenType
from app.infrastructure.sockets.contracts import SocketPrincipal


class SocketAuthenticationError(PermissionError):
    pass


@dataclass
class JwtSocketAuthenticator:
    token_manager: JwtTokenManager
    expected_type: TokenType = TokenType.ACCESS

    def authenticate(self, token: str) -> SocketPrincipal:
        try:
            claims = self.token_manager.decode_and_validate(token, expected_type=self.expected_type)
        except Exception as exc:
            raise SocketAuthenticationError("Socket authentication failed.") from exc

        actor_id = claims.get("sub")
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise SocketAuthenticationError("Socket token subject is missing.")
        tenant_id = claims.get("tenant_id")
        return SocketPrincipal(
            actor_id=actor_id,
            tenant_id=tenant_id if isinstance(tenant_id, str) else None,
            claims=claims,
        )


def extract_socket_token(
    *,
    query_params: Mapping[str, str] | None = None,
    headers: Mapping[str, str] | None = None,
    query_key: str = "token",
    header_name: str = "authorization",
) -> str | None:
    query = query_params or {}
    token = query.get(query_key)
    if isinstance(token, str) and token.strip():
        return token.strip()

    resolved_headers = {key.lower(): value for key, value in (headers or {}).items()}
    raw_auth = resolved_headers.get(header_name.lower())
    if not isinstance(raw_auth, str):
        return None
    prefix = "bearer "
    if raw_auth.lower().startswith(prefix):
        candidate = raw_auth[len(prefix) :].strip()
        return candidate if candidate else None
    return raw_auth.strip() or None
""",
    "app/infrastructure/sockets/hub.py": """from collections import defaultdict
from dataclasses import dataclass, field
from inspect import isawaitable
from typing import Any

from app.infrastructure.sockets.contracts import SocketConnection, SocketEnvelope, SocketPrincipal


@dataclass
class InMemorySocketHub:
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
""",
    "app/presentation/routers/realtime.py": """# WebSocket /realtime/ws: JWT handshake, rooms, broadcast, presence.
# JSON frames: type ping|join|leave|broadcast|presence — see docs/guides/realtime-websocket.md
# Token: ?token=<access_jwt> or Authorization: Bearer. Hub is in-memory (single process).

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.core.auth import JwtTokenManager
from app.core.config import get_settings
from app.infrastructure.sockets import (
    InMemorySocketHub,
    JwtSocketAuthenticator,
    SocketAuthenticationError,
    extract_socket_token,
)
from app.infrastructure.sockets.contracts import SocketPrincipal

router = APIRouter(prefix="/realtime", tags=["realtime"])


def build_jwt_token_manager() -> JwtTokenManager | None:
    s = get_settings()
    if not s.auth.jwt_enabled:
        return None
    return JwtTokenManager(
        secret=s.auth.jwt_secret,
        access_ttl=timedelta(minutes=s.auth.access_token_minutes),
        refresh_ttl=timedelta(days=s.auth.refresh_token_days),
    )


def register_socket_state(app: FastAPI) -> None:
    app.state.socket_hub = InMemorySocketHub()


@router.websocket("/ws")
async def realtime_websocket(websocket: WebSocket) -> None:
    settings = get_settings()
    token = extract_socket_token(
        query_params=dict(websocket.query_params),
        headers=dict(websocket.headers),
    )
    principal: SocketPrincipal | None = None
    if settings.realtime.require_access_jwt:
        if not token:
            await websocket.close(code=1008)
            return
        if not settings.auth.jwt_enabled:
            await websocket.close(code=1008)
            return
        manager = build_jwt_token_manager()
        if manager is None:
            await websocket.close(code=1008)
            return
        try:
            principal = JwtSocketAuthenticator(manager).authenticate(token)
        except SocketAuthenticationError:
            await websocket.close(code=1008)
            return
    else:
        if token and settings.auth.jwt_enabled:
            manager = build_jwt_token_manager()
            if manager is not None:
                try:
                    principal = JwtSocketAuthenticator(manager).authenticate(token)
                except SocketAuthenticationError:
                    await websocket.close(code=1008)
                    return
        if principal is None:
            principal = SocketPrincipal(actor_id="anonymous", tenant_id=None, claims={})

    hub: InMemorySocketHub = websocket.app.state.socket_hub
    await websocket.accept()
    connection_id = hub.register(websocket, principal)
    await websocket.send_json(
        {
            "type": "connected",
            "connection_id": connection_id,
            "actor_id": principal.actor_id,
            "tenant_id": principal.tenant_id,
        }
    )
    try:
        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "code": "INVALID_JSON", "message": "Payload must be JSON."}
                )
                continue
            if not isinstance(message, dict):
                await websocket.send_json(
                    {"type": "error", "code": "INVALID_SHAPE", "message": "Payload must be a JSON object."}
                )
                continue
            await _handle_client_message(websocket, hub, connection_id, message)
    finally:
        hub.disconnect(connection_id)


async def _handle_client_message(
    websocket: WebSocket,
    hub: InMemorySocketHub,
    connection_id: str,
    message: dict[str, Any],
) -> None:
    msg_type = message.get("type")
    if msg_type == "ping":
        await websocket.send_json({"type": "pong"})
        return
    if msg_type == "join":
        room = message.get("room")
        if not isinstance(room, str) or not room.strip():
            await websocket.send_json(
                {"type": "error", "code": "INVALID_ROOM", "message": "join requires non-empty string room."}
            )
            return
        normalized = room.strip()
        ok = hub.join_room(normalized, connection_id)
        await websocket.send_json({"type": "joined", "room": normalized, "ok": ok})
        return
    if msg_type == "leave":
        room = message.get("room")
        if not isinstance(room, str) or not room.strip():
            await websocket.send_json(
                {"type": "error", "code": "INVALID_ROOM", "message": "leave requires non-empty string room."}
            )
            return
        normalized = room.strip()
        ok = hub.leave_room(normalized, connection_id)
        await websocket.send_json({"type": "left", "room": normalized, "ok": ok})
        return
    if msg_type == "broadcast":
        room = message.get("room")
        event = message.get("event")
        if not isinstance(room, str) or not room.strip():
            await websocket.send_json(
                {"type": "error", "code": "INVALID_ROOM", "message": "broadcast requires non-empty string room."}
            )
            return
        if not isinstance(event, str) or not event.strip():
            await websocket.send_json(
                {"type": "error", "code": "INVALID_EVENT", "message": "broadcast requires non-empty string event."}
            )
            return
        normalized = room.strip()
        if connection_id not in hub.room_members(normalized):
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "NOT_IN_ROOM",
                    "message": "Join the room before broadcasting.",
                }
            )
            return
        payload = message.get("payload")
        if payload is not None and not isinstance(payload, dict):
            await websocket.send_json(
                {"type": "error", "code": "INVALID_PAYLOAD", "message": "payload must be an object."}
            )
            return
        delivered = await hub.broadcast(
            room=normalized,
            event=event.strip(),
            payload=payload or {},
            exclude_connection_id=connection_id,
        )
        await websocket.send_json({"type": "broadcast_result", "room": normalized, "delivered": delivered})
        return
    if msg_type == "presence":
        room = message.get("room")
        if not isinstance(room, str) or not room.strip():
            await websocket.send_json(
                {"type": "error", "code": "INVALID_ROOM", "message": "presence requires non-empty string room."}
            )
            return
        normalized = room.strip()
        members = hub.room_members(normalized)
        presence = hub.room_presence(normalized)
        await websocket.send_json(
            {
                "type": "presence_result",
                "room": normalized,
                "connection_ids": list(members),
                "by_actor": presence,
            }
        )
        return

    await websocket.send_json(
        {"type": "error", "code": "UNKNOWN_TYPE", "message": f"Unknown type: {msg_type!r}."}
    )
""",
}
