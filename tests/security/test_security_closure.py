"""Security regression tests (edge controls, auth boundaries)."""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from eitohforge_sdk.core.error_middleware import register_error_handlers
from eitohforge_sdk.core.rate_limit import InMemoryRateLimiter, RateLimitRule, register_rate_limiter_middleware
from eitohforge_sdk.core.security import SecurityPrincipal, require_roles


@pytest.mark.security
def test_admin_route_rejects_missing_role_headers() -> None:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/admin/x")
    def x(_: SecurityPrincipal = Depends(require_roles("admin"))) -> dict[str, str]:
        return {"ok": "true"}

    response = TestClient(app, raise_server_exceptions=False).get("/admin/x")
    assert response.status_code == 403
    assert response.json().get("error", {}).get("code") == "PERMISSION_DENIED"


@pytest.mark.security
def test_admin_route_accepts_role_header() -> None:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/admin/x")
    def x(_: SecurityPrincipal = Depends(require_roles("admin"))) -> dict[str, str]:
        return {"ok": "true"}

    response = TestClient(app).get("/admin/x", headers={"x-actor-id": "u1", "x-roles": "admin"})
    assert response.status_code == 200


@pytest.mark.security
def test_rate_limit_returns_429_after_burst() -> None:
    app = FastAPI()
    rule = RateLimitRule(max_requests=2, window_seconds=60, key_headers=("x-actor-id",))
    register_rate_limiter_middleware(app, rule, limiter=InMemoryRateLimiter())
    client = TestClient(app)

    @app.get("/r")
    def r() -> dict[str, str]:
        return {"ok": "true"}

    assert client.get("/r", headers={"x-actor-id": "a"}).status_code == 200
    assert client.get("/r", headers={"x-actor-id": "a"}).status_code == 200
    blocked = client.get("/r", headers={"x-actor-id": "a"})
    assert blocked.status_code == 429
    assert blocked.json().get("error", {}).get("code") == "RATE_LIMIT_EXCEEDED"
