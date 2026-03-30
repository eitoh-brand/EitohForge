from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from eitohforge_sdk.core.rate_limit import InMemoryRateLimiter, RateLimitRule, register_rate_limiter_middleware


def test_rate_limit_middleware_blocks_after_limit() -> None:
    app = FastAPI()
    register_rate_limiter_middleware(app, RateLimitRule(max_requests=2, window_seconds=60))

    @app.get("/limited")
    def limited() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)
    headers = {"x-actor-id": "u1"}
    assert client.get("/limited", headers=headers).status_code == 200
    assert client.get("/limited", headers=headers).status_code == 200
    blocked = client.get("/limited", headers=headers)
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert "Retry-After" in blocked.headers


def test_rate_limit_middleware_scope_path_prefix() -> None:
    app = FastAPI()
    register_rate_limiter_middleware(
        app,
        RateLimitRule(max_requests=1, window_seconds=60, scope_path_prefix="/protected"),
    )

    @app.get("/public")
    def public() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/protected/resource")
    def protected() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)
    headers = {"x-actor-id": "u2"}
    assert client.get("/public", headers=headers).status_code == 200
    assert client.get("/public", headers=headers).status_code == 200
    assert client.get("/protected/resource", headers=headers).status_code == 200
    assert client.get("/protected/resource", headers=headers).status_code == 429


def test_in_memory_limiter_resets_after_window() -> None:
    clock = {"now": datetime(2026, 1, 1, tzinfo=UTC)}
    limiter = InMemoryRateLimiter(now_provider=lambda: clock["now"])
    rule = RateLimitRule(max_requests=1, window_seconds=5)
    assert limiter.allow("actor:u3", rule) == (True, 0)
    assert limiter.allow("actor:u3", rule)[0] is False
    clock["now"] = clock["now"].replace(second=clock["now"].second + 6)
    assert limiter.allow("actor:u3", rule) == (True, 0)

