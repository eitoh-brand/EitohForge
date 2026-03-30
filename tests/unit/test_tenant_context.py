from __future__ import annotations

from fastapi import FastAPI
from fastapi import Request
from fastapi.testclient import TestClient

from eitohforge_sdk.core.tenant import TenantContext, TenantIsolationRule, get_request_tenant_context, register_tenant_context_middleware


def test_tenant_middleware_blocks_write_without_tenant_context() -> None:
    app = FastAPI()
    register_tenant_context_middleware(app, TenantIsolationRule())

    @app.post("/items")
    def create_item() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(app)
    response = client.post("/items")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_CONTEXT_REQUIRED"


def test_tenant_middleware_blocks_cross_tenant_access() -> None:
    app = FastAPI()
    register_tenant_context_middleware(app, TenantIsolationRule())

    @app.get("/tenant-bound")
    def tenant_bound() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(app)
    response = client.get(
        "/tenant-bound",
        headers={
            "x-tenant-id": "tenant-a",
            "x-resource-tenant-id": "tenant-b",
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_ACCESS_DENIED"


def test_tenant_middleware_attaches_tenant_context() -> None:
    app = FastAPI()
    register_tenant_context_middleware(app, TenantIsolationRule())

    @app.get("/tenant-context-read")
    def tenant_context_read(request: Request) -> dict[str, str | None]:
        context = get_request_tenant_context(request)
        return {"tenant_id": context.tenant_id, "actor_id": context.actor_id}

    client = TestClient(app)
    response = client.get(
        "/tenant-context-read",
        headers={"x-tenant-id": "tenant-a", "x-actor-id": "actor-1"},
    )
    assert response.status_code == 200
    assert response.json() == {"tenant_id": "tenant-a", "actor_id": "actor-1"}


def test_tenant_context_current_reads_contextvar() -> None:
    app = FastAPI()
    register_tenant_context_middleware(app, TenantIsolationRule())

    @app.get("/tenant-current")
    def tenant_current() -> dict[str, str | None]:
        ctx = TenantContext.current()
        return {"tenant_id": ctx.tenant_id, "actor_id": ctx.actor_id}

    client = TestClient(app)
    response = client.get(
        "/tenant-current",
        headers={"x-tenant-id": "tenant-a", "x-actor-id": "actor-1"},
    )
    assert response.status_code == 200
    assert response.json() == {"tenant_id": "tenant-a", "actor_id": "actor-1"}


def test_tenant_context_current_propagates_into_async_tasks() -> None:
    import asyncio

    app = FastAPI()
    register_tenant_context_middleware(app, TenantIsolationRule(required_for_write_methods=False))

    @app.get("/spawn")
    async def spawn_task() -> dict[str, str | None]:
        async def inner() -> str | None:
            ctx = TenantContext.current()
            return ctx.tenant_id

        task = asyncio.create_task(inner())
        return {"tenant_id": await task}

    client = TestClient(app)
    response = client.get("/spawn", headers={"x-tenant-id": "tenant-a", "x-actor-id": "actor-1"})
    assert response.status_code == 200
    assert response.json() == {"tenant_id": "tenant-a"}
