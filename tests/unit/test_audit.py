from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from eitohforge_sdk.core.audit import AuditRule, InMemoryAuditSink, register_audit_middleware


def test_audit_middleware_records_write_requests_with_security_context() -> None:
    app = FastAPI()
    sink = InMemoryAuditSink()
    register_audit_middleware(app, AuditRule(), sink=sink)

    @app.post("/orders")
    def create_order() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)
    response = client.post(
        "/orders",
        headers={
            "x-actor-id": "actor-1",
            "x-tenant-id": "tenant-a",
            "x-request-id": "req-1",
            "x-trace-id": "trace-1",
        },
    )
    assert response.status_code == 200
    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.action == "http.post"
    assert event.path == "/orders"
    assert event.method == "POST"
    assert event.actor_id == "actor-1"
    assert event.tenant_id == "tenant-a"
    assert event.request_id == "req-1"
    assert event.trace_id == "trace-1"


def test_audit_middleware_ignores_non_configured_methods() -> None:
    app = FastAPI()
    sink = InMemoryAuditSink()
    register_audit_middleware(app, AuditRule(methods=("POST",)), sink=sink)

    @app.get("/read")
    def read() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/read")
    assert response.status_code == 200
    assert sink.events == []

