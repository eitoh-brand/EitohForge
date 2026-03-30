from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from eitohforge_sdk.core.observability import (
    InMemoryMetricsSink,
    ObservabilityRule,
    get_request_id,
    get_request_trace_id,
    register_observability_middleware,
)


def test_observability_middleware_sets_trace_and_request_ids() -> None:
    app = FastAPI()
    sink = InMemoryMetricsSink()
    register_observability_middleware(app, ObservabilityRule(), metrics_sink=sink)

    @app.get("/hello")
    def hello(request: Request) -> dict[str, str | None]:
        return {
            "trace_id": get_request_trace_id(request),
            "request_id": get_request_id(request),
        }

    client = TestClient(app)
    response = client.get("/hello")
    assert response.status_code == 200
    payload = response.json()
    assert payload["trace_id"] is not None
    assert payload["request_id"] is not None
    assert response.headers.get("x-trace-id")
    assert response.headers.get("x-request-id")
    assert any(key[0] == "http.requests.total" for key in sink.counters)


def test_observability_middleware_uses_incoming_trace_header() -> None:
    app = FastAPI()
    register_observability_middleware(app, ObservabilityRule())

    @app.get("/ping")
    def ping(request: Request) -> dict[str, str | None]:
        return {"trace_id": get_request_trace_id(request)}

    client = TestClient(app)
    response = client.get("/ping", headers={"x-trace-id": "trace-123"})
    assert response.status_code == 200
    assert response.json()["trace_id"] == "trace-123"
    assert response.headers.get("x-trace-id") == "trace-123"

