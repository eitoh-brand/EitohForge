from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from eitohforge_sdk.core.auth import JwtTokenManager
from eitohforge_sdk.core.config import AppSettings, AuthSettings, RealtimeSettings
from eitohforge_sdk.infrastructure.sockets.realtime_router import attach_socket_hub, build_realtime_router

_SECRET = "unit-test-secret-value-at-least-32-chars"


def _client(settings: AppSettings) -> TestClient:
    app = FastAPI()
    attach_socket_hub(app, settings_provider=lambda: settings)
    app.include_router(build_realtime_router(settings_provider=lambda: settings))
    return TestClient(app)


def test_realtime_ws_anonymous_when_jwt_not_required() -> None:
    settings = AppSettings(
        auth=AuthSettings(jwt_secret=_SECRET, jwt_enabled=True),
        realtime=RealtimeSettings(enabled=True, require_access_jwt=False),
    )
    client = _client(settings)
    with client.websocket_connect("/realtime/ws") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        assert msg["actor_id"] == "anonymous"


def test_realtime_ws_rejects_connection_when_jwt_required_but_missing() -> None:
    settings = AppSettings(
        auth=AuthSettings(jwt_secret=_SECRET, jwt_enabled=True),
        realtime=RealtimeSettings(enabled=True, require_access_jwt=True),
    )
    client = _client(settings)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/realtime/ws"):
            pass
    assert exc_info.value.code == 1008


def test_realtime_ws_accepts_query_token_when_jwt_required() -> None:
    settings = AppSettings(
        auth=AuthSettings(jwt_secret=_SECRET, jwt_enabled=True),
        realtime=RealtimeSettings(enabled=True, require_access_jwt=True),
    )
    manager = JwtTokenManager(secret=_SECRET)
    pair = manager.issue_token_pair(subject="ws-user-1", tenant_id="t-1")
    client = _client(settings)
    with client.websocket_connect(f"/realtime/ws?token={pair.access_token}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        assert msg["actor_id"] == "ws-user-1"


def test_realtime_ws_ping_pong_and_invalid_json() -> None:
    settings = AppSettings(
        auth=AuthSettings(jwt_secret=_SECRET, jwt_enabled=True),
        realtime=RealtimeSettings(enabled=True, require_access_jwt=False),
    )
    client = _client(settings)
    with client.websocket_connect("/realtime/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "ping"})
        assert ws.receive_json() == {"type": "pong"}
        ws.send_text("not-json")
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "INVALID_JSON"


def test_realtime_ws_join_broadcast_roundtrip() -> None:
    settings = AppSettings(
        auth=AuthSettings(jwt_secret=_SECRET, jwt_enabled=True),
        realtime=RealtimeSettings(enabled=True, require_access_jwt=False),
    )
    client = _client(settings)
    with client.websocket_connect("/realtime/ws") as ws_a:
        ws_a.receive_json()
        with client.websocket_connect("/realtime/ws") as ws_b:
            ws_b.receive_json()
            ws_a.send_json({"type": "join", "room": "r1"})
            assert ws_a.receive_json()["type"] == "joined"
            ws_b.send_json({"type": "join", "room": "r1"})
            assert ws_b.receive_json()["type"] == "joined"
            ws_a.send_json({"type": "broadcast", "room": "r1", "event": "e1", "payload": {"k": 1}})
            res = ws_a.receive_json()
            assert res["type"] == "broadcast_result"
            assert res["delivered"] == 1
            incoming = ws_b.receive_json()
            assert incoming["event"] == "e1"
            assert incoming["payload"] == {"k": 1}


def test_realtime_ws_direct_requires_non_anonymous_identity() -> None:
    settings = AppSettings(
        auth=AuthSettings(jwt_secret=_SECRET, jwt_enabled=True),
        realtime=RealtimeSettings(enabled=True, require_access_jwt=False),
    )
    client = _client(settings)
    with client.websocket_connect("/realtime/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "direct", "target_actor_id": "bob", "event": "x"})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "DIRECT_REQUIRES_IDENTITY"


def test_realtime_ws_direct_delivers_to_target_actor() -> None:
    settings = AppSettings(
        auth=AuthSettings(jwt_secret=_SECRET, jwt_enabled=True),
        realtime=RealtimeSettings(enabled=True, require_access_jwt=False),
    )
    manager = JwtTokenManager(secret=_SECRET)
    alice = manager.issue_token_pair(subject="alice", tenant_id="t1")
    bob = manager.issue_token_pair(subject="bob", tenant_id="t1")
    client = _client(settings)
    with client.websocket_connect(f"/realtime/ws?token={bob.access_token}") as ws_b:
        ws_b.receive_json()
        with client.websocket_connect(f"/realtime/ws?token={alice.access_token}") as ws_a:
            ws_a.receive_json()
            ws_a.send_json({"type": "direct", "target_actor_id": "bob", "event": "hello", "payload": {"n": 1}})
            res = ws_a.receive_json()
            assert res["type"] == "direct_result"
            assert res["delivered"] == 1
            incoming = ws_b.receive_json()
            assert incoming["event"] == "hello"
            assert incoming["room"] == "__direct__"
            assert incoming["from_actor_id"] == "alice"
            assert incoming["target_actor_id"] == "bob"
