from __future__ import annotations

import re
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from eitohforge_sdk.core.observability import (
    InMemoryMetricsSink,
    PrometheusMetricsSink,
    ObservabilityRule,
    get_request_id,
    get_request_trace_id,
    register_observability_middleware,
    register_prometheus_metrics_endpoint,
)
from eitohforge_sdk.core.config import AppSettings
from eitohforge_sdk.core.forge_application import ForgeAppBuildConfig, build_forge_app
from eitohforge_sdk.core.config import AuthSettings


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


def test_prometheus_metrics_endpoint_exposes_request_counters() -> None:
    app = FastAPI()
    sink = PrometheusMetricsSink(namespace="test")

    register_prometheus_metrics_endpoint(app, metrics_sink=sink, path="/metrics")
    register_observability_middleware(
        app,
        ObservabilityRule(
            enabled=True,
            enable_metrics=True,
            enable_logging=False,
            enable_tracing=False,
            trace_header="x-trace-id",
            request_id_header="x-request-id",
        ),
        metrics_sink=sink,
    )

    @app.get("/hello")
    def hello() -> dict[str, str]:
        return {"ok": "1"}

    client = TestClient(app)
    resp = client.get("/hello")
    assert resp.status_code == 200

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    text = metrics.text
    assert "test_http_requests_total" in text
    assert "/hello" in text


def test_build_forge_app_configures_otel_and_trace_id_is_hex() -> None:
    settings = AppSettings(
        auth=AuthSettings(jwt_secret="unit-test-secret-value-at-least-32-chars"),
        realtime={"enabled": False},
        observability={
            "enabled": True,
            "enable_metrics": False,
            "enable_logging": False,
            "enable_tracing": True,
            "otel_enabled": True,
            "otel_otlp_http_endpoint": None,
        },
    )

    app = build_forge_app(
        build=ForgeAppBuildConfig(
            wire_feature_flags=False,
            settings_provider=lambda: settings,
        )
    )

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"ok": "1"}

    client = TestClient(app)
    resp = client.get("/ping")
    assert resp.status_code == 200
    trace_id = resp.headers.get("x-trace-id")
    assert trace_id is not None
    assert re.fullmatch(r"[0-9a-f]{32}", trace_id)

