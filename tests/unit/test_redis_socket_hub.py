from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from eitohforge_sdk.core.config import AppSettings, AuthSettings, RealtimeSettings
from eitohforge_sdk.infrastructure.sockets import (
    InMemorySocketHub,
    RedisFanoutSocketHub,
    SocketPrincipal,
    build_socket_hub_for_settings,
)
from eitohforge_sdk.infrastructure.sockets.redis_hub import CLUSTER_BROADCAST_SCHEMA_VERSION, dispatch_redis_fanout_payload


class FakeSocketConnection:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.messages.append(dict(payload))


def test_build_socket_hub_in_memory_without_redis_url() -> None:
    settings = AppSettings(
        auth=AuthSettings(jwt_secret="x" * 32),
        realtime=RealtimeSettings(redis_url=None),
    )
    hub = build_socket_hub_for_settings(settings)
    assert type(hub) is InMemorySocketHub


@pytest.mark.parametrize("url", ["redis://localhost:6379/0", "  redis://localhost:6379/1  "])
def test_build_socket_hub_wraps_when_redis_url_set(url: str) -> None:
    settings = AppSettings(
        auth=AuthSettings(jwt_secret="x" * 32),
        realtime=RealtimeSettings(redis_url=url),
    )
    hub = build_socket_hub_for_settings(settings)
    assert isinstance(hub, RedisFanoutSocketHub)
    asyncio.run(hub.aclose())


def test_redis_fanout_broadcast_publishes_json() -> None:
    inner = InMemorySocketHub()
    mock_redis = MagicMock()
    mock_redis.publish = AsyncMock(return_value=1)
    hub = RedisFanoutSocketHub(
        _inner=inner,
        _redis_publish=mock_redis,
        _channel="test:rt",
        _publisher_id="worker-a",
    )
    sock = FakeSocketConnection()
    principal = SocketPrincipal(actor_id="u1")
    cid = hub.register(sock, principal)
    assert hub.join_room("room1", cid) is True

    delivered = asyncio.run(
        hub.broadcast(room="room1", event="evt", payload={"n": 1}, exclude_connection_id=cid)
    )
    assert delivered == 0
    mock_redis.publish.assert_awaited_once()
    ch, body = mock_redis.publish.await_args[0]
    assert ch == "test:rt"
    data = json.loads(body)
    assert data["v"] == CLUSTER_BROADCAST_SCHEMA_VERSION
    assert data["kind"] == "broadcast"
    assert data["publisher_id"] == "worker-a"
    assert data["room"] == "room1"
    assert data["event"] == "evt"
    assert data["payload"] == {"n": 1}
    asyncio.run(hub.aclose())


def test_dispatch_skips_same_publisher_delivers_to_peer_worker() -> None:
    inner_b = InMemorySocketHub()
    mock_b = MagicMock()
    mock_b.publish = AsyncMock(return_value=1)
    hub_b = RedisFanoutSocketHub(
        _inner=inner_b,
        _redis_publish=mock_b,
        _channel="ch",
        _publisher_id="worker-b",
    )
    sock = FakeSocketConnection()
    cid = hub_b.register(sock, SocketPrincipal(actor_id="u2"))
    hub_b.join_room("r", cid)

    same = asyncio.run(
        dispatch_redis_fanout_payload(
            hub_b,
            json.dumps(
                {
                    "v": CLUSTER_BROADCAST_SCHEMA_VERSION,
                    "publisher_id": "worker-b",
                    "room": "r",
                    "event": "e",
                    "payload": {},
                }
            ),
        )
    )
    assert same == 0
    assert sock.messages == []

    other = asyncio.run(
        dispatch_redis_fanout_payload(
            hub_b,
            json.dumps(
                {
                    "v": CLUSTER_BROADCAST_SCHEMA_VERSION,
                    "publisher_id": "worker-a",
                    "room": "r",
                    "event": "e",
                    "payload": {"x": True},
                }
            ),
        )
    )
    assert other == 1
    assert len(sock.messages) == 1
    assert sock.messages[0]["event"] == "e"
    assert sock.messages[0]["payload"] == {"x": True}
    asyncio.run(hub_b.aclose())


def test_redis_fanout_direct_publishes_kind_direct() -> None:
    inner = InMemorySocketHub()
    mock_redis = MagicMock()
    mock_redis.publish = AsyncMock(return_value=1)
    hub = RedisFanoutSocketHub(
        _inner=inner,
        _redis_publish=mock_redis,
        _channel="test:rt",
        _publisher_id="worker-a",
    )
    sock = FakeSocketConnection()
    cid = hub.register(sock, SocketPrincipal(actor_id="bob"))
    delivered = asyncio.run(
        hub.send_direct_to_actor(
            target_actor_id="bob",
            event="dm",
            payload={"t": 1},
            from_actor_id="alice",
            exclude_connection_id=cid,
        )
    )
    assert delivered == 0
    mock_redis.publish.assert_awaited_once()
    data = json.loads(mock_redis.publish.await_args[0][1])
    assert data["kind"] == "direct"
    assert data["target_actor_id"] == "bob"
    assert data["from_actor_id"] == "alice"
    asyncio.run(hub.aclose())


def test_dispatch_direct_skips_same_publisher() -> None:
    inner = InMemorySocketHub()
    mock_r = MagicMock()
    mock_r.publish = AsyncMock(return_value=1)
    hub = RedisFanoutSocketHub(_inner=inner, _redis_publish=mock_r, _channel="c", _publisher_id="w1")
    sock = FakeSocketConnection()
    hub.register(sock, SocketPrincipal(actor_id="bob"))
    n = asyncio.run(
        dispatch_redis_fanout_payload(
            hub,
            json.dumps(
                {
                    "v": CLUSTER_BROADCAST_SCHEMA_VERSION,
                    "kind": "direct",
                    "publisher_id": "w1",
                    "target_actor_id": "bob",
                    "event": "e",
                    "payload": {},
                    "from_actor_id": "alice",
                }
            ),
        )
    )
    assert n == 0
    assert sock.messages == []
    asyncio.run(hub.aclose())


def test_dispatch_no_op_on_plain_in_memory_hub() -> None:
    hub = InMemorySocketHub()
    n = asyncio.run(
        dispatch_redis_fanout_payload(
            hub,
            json.dumps(
                {
                    "v": CLUSTER_BROADCAST_SCHEMA_VERSION,
                    "publisher_id": "a",
                    "room": "r",
                    "event": "e",
                    "payload": {},
                }
            ),
        )
    )
    assert n == 0
