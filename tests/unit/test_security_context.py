from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from eitohforge_sdk.core.security_context import (
    SecurityContext,
    build_security_context_from_headers,
    get_request_security_context,
    register_security_context_middleware,
)


def test_build_security_context_from_headers() -> None:
    context = build_security_context_from_headers(
        {
            "x-actor-id": "actor-1",
            "x-tenant-id": "tenant-a",
            "x-roles": "admin,user",
            "x-permissions": "users:read,users:write",
            "x-request-id": "req-1",
            "x-trace-id": "trace-1",
            "x-session-id": "sess-1",
        }
    )
    assert context.actor_id == "actor-1"
    assert context.tenant_id == "tenant-a"
    assert context.roles == ("admin", "user")
    assert context.permissions == ("users:read", "users:write")


def test_security_context_middleware_attaches_context_to_request_state() -> None:
    app = FastAPI()
    register_security_context_middleware(app)

    @app.get("/me")
    def me(request: Request) -> dict[str, str]:
        context = get_request_security_context(request)
        assert isinstance(context, SecurityContext)
        return {
            "actor_id": context.actor_id or "",
            "tenant_id": context.tenant_id or "",
        }

    client = TestClient(app)
    response = client.get("/me", headers={"x-actor-id": "actor-2", "x-tenant-id": "tenant-b"})
    assert response.status_code == 200
    assert response.json() == {"actor_id": "actor-2", "tenant_id": "tenant-b"}

