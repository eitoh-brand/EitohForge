from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import pytest

from eitohforge_sdk.core.auth import JwtTokenManager
from eitohforge_sdk.infrastructure.sockets import (
    InMemorySocketHub,
    JwtSocketAuthenticator,
    SocketAuthenticationError,
    SocketPrincipal,
    extract_socket_token,
)


class FakeSocketConnection:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []
        self.closed = False

    async def send_json(self, payload: Mapping[str, Any]) -> None:
        self.messages.append(dict(payload))

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        _ = (code, reason)
        self.closed = True


def test_jwt_socket_authenticator_validates_access_token() -> None:
    manager = JwtTokenManager(secret="dev-secret-value-at-least-32-characters")
    pair = manager.issue_token_pair(subject="actor-1", tenant_id="tenant-1")
    principal = JwtSocketAuthenticator(manager).authenticate(pair.access_token)
    assert principal.actor_id == "actor-1"
    assert principal.tenant_id == "tenant-1"


def test_jwt_socket_authenticator_rejects_refresh_token_for_socket_auth() -> None:
    manager = JwtTokenManager(secret="dev-secret-value-at-least-32-characters")
    pair = manager.issue_token_pair(subject="actor-1")
    authenticator = JwtSocketAuthenticator(manager)
    with pytest.raises(SocketAuthenticationError):
        authenticator.authenticate(pair.refresh_token)


def test_socket_hub_tracks_rooms_presence_and_broadcasts() -> None:
    hub = InMemorySocketHub()
    socket_a = FakeSocketConnection()
    socket_b = FakeSocketConnection()
    principal = SocketPrincipal(actor_id="actor-1", tenant_id="tenant-1")
    conn_a = hub.register(socket_a, principal)
    conn_b = hub.register(socket_b, principal)
    assert hub.join_room("room.orders", conn_a) is True
    assert hub.join_room("room.orders", conn_b) is True

    delivered = asyncio.run(
        hub.broadcast(room="room.orders", event="orders.updated", payload={"order_id": "ord-1"})
    )
    assert delivered == 2
    assert len(socket_a.messages) == 1
    assert len(socket_b.messages) == 1
    assert socket_a.messages[0]["event"] == "orders.updated"
    assert hub.room_members("room.orders") == tuple(sorted((conn_a, conn_b)))
    presence = hub.room_presence("room.orders")
    assert set(presence.keys()) == {"actor-1"}
    assert set(presence["actor-1"]) == {conn_a, conn_b}

    assert hub.leave_room("room.orders", conn_a) is True
    assert hub.disconnect(conn_b) is True
    assert hub.room_members("room.orders") == ()


def test_extract_socket_token_from_query_or_authorization_header() -> None:
    assert (
        extract_socket_token(
            query_params={"token": "query-token"},
            headers={"authorization": "Bearer header-token"},
        )
        == "query-token"
    )
    assert (
        extract_socket_token(
            query_params={},
            headers={"authorization": "Bearer header-token"},
        )
        == "header-token"
    )
