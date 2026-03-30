"""FastAPI WebSocket router for JWT-backed rooms and broadcast (shared by `build_forge_app` and optional app wiring)."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect

from eitohforge_sdk.core.auth import JwtTokenManager
from eitohforge_sdk.core.config import AppSettings
from eitohforge_sdk.infrastructure.sockets.auth import (
    JwtSocketAuthenticator,
    SocketAuthenticationError,
    extract_socket_token,
)
from eitohforge_sdk.infrastructure.sockets.contracts import SocketHub, SocketPrincipal
from eitohforge_sdk.infrastructure.sockets.redis_hub import build_socket_hub_for_settings


def attach_socket_hub(app: FastAPI, *, settings_provider: Callable[[], AppSettings]) -> None:
    """Attach ``app.state.socket_hub`` (in-memory, or Redis fan-out when ``RealtimeSettings.redis_url`` is set)."""
    app.state.socket_hub = build_socket_hub_for_settings(settings_provider())


def attach_in_memory_socket_hub(app: FastAPI) -> None:
    """Attach the socket hub using :func:`get_settings` (backward-compatible alias for ``attach_socket_hub``)."""
    from eitohforge_sdk.core.config import get_settings

    attach_socket_hub(app, settings_provider=get_settings)


def _build_jwt_manager(settings: AppSettings) -> JwtTokenManager | None:
    if not settings.auth.jwt_enabled:
        return None
    return JwtTokenManager(
        secret=settings.auth.jwt_secret,
        access_ttl=timedelta(minutes=settings.auth.access_token_minutes),
        refresh_ttl=timedelta(days=settings.auth.refresh_token_days),
    )


def build_realtime_router(*, settings_provider: Callable[[], AppSettings]) -> APIRouter:
    """Build ``/realtime/ws`` using ``AppSettings.auth`` and ``AppSettings.realtime``."""
    router = APIRouter(prefix="/realtime", tags=["realtime"])

    @router.websocket("/ws")
    async def realtime_websocket(websocket: WebSocket) -> None:
        settings = settings_provider()
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
            manager = _build_jwt_manager(settings)
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
                manager = _build_jwt_manager(settings)
                if manager is not None:
                    try:
                        principal = JwtSocketAuthenticator(manager).authenticate(token)
                    except SocketAuthenticationError:
                        await websocket.close(code=1008)
                        return
            if principal is None:
                principal = SocketPrincipal(actor_id="anonymous", tenant_id=None, claims={})

        hub: SocketHub = websocket.app.state.socket_hub
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
                        {
                            "type": "error",
                            "code": "INVALID_SHAPE",
                            "message": "Payload must be a JSON object.",
                        }
                    )
                    continue
                await _handle_client_message(websocket, hub, connection_id, message, principal)
        finally:
            hub.disconnect(connection_id)

    return router


async def _handle_client_message(
    websocket: WebSocket,
    hub: SocketHub,
    connection_id: str,
    message: dict[str, Any],
    principal: SocketPrincipal,
) -> None:
    msg_type = message.get("type")
    if msg_type == "ping":
        await websocket.send_json({"type": "pong"})
        return
    if msg_type == "join":
        room = message.get("room")
        if not isinstance(room, str) or not room.strip():
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "INVALID_ROOM",
                    "message": "join requires non-empty string room.",
                }
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
                {
                    "type": "error",
                    "code": "INVALID_ROOM",
                    "message": "leave requires non-empty string room.",
                }
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
                {
                    "type": "error",
                    "code": "INVALID_ROOM",
                    "message": "broadcast requires non-empty string room.",
                }
            )
            return
        if not isinstance(event, str) or not event.strip():
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "INVALID_EVENT",
                    "message": "broadcast requires non-empty string event.",
                }
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
    if msg_type == "direct":
        if principal.actor_id == "anonymous":
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "DIRECT_REQUIRES_IDENTITY",
                    "message": "direct messages require a non-anonymous principal (JWT or application identity).",
                }
            )
            return
        target_actor_id = message.get("target_actor_id")
        event = message.get("event")
        if not isinstance(target_actor_id, str) or not target_actor_id.strip():
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "INVALID_TARGET",
                    "message": "direct requires non-empty string target_actor_id.",
                }
            )
            return
        if not isinstance(event, str) or not event.strip():
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "INVALID_EVENT",
                    "message": "direct requires non-empty string event.",
                }
            )
            return
        payload = message.get("payload")
        if payload is not None and not isinstance(payload, dict):
            await websocket.send_json(
                {"type": "error", "code": "INVALID_PAYLOAD", "message": "payload must be an object."}
            )
            return
        delivered = await hub.send_direct_to_actor(
            target_actor_id=target_actor_id.strip(),
            event=event.strip(),
            payload=payload or {},
            from_actor_id=principal.actor_id,
            exclude_connection_id=connection_id,
        )
        await websocket.send_json(
            {"type": "direct_result", "target_actor_id": target_actor_id.strip(), "delivered": delivered}
        )
        return
    if msg_type == "presence":
        room = message.get("room")
        if not isinstance(room, str) or not room.strip():
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "INVALID_ROOM",
                    "message": "presence requires non-empty string room.",
                }
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
