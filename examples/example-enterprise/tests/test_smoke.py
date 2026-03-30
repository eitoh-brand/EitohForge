"""Smoke tests for example-enterprise."""

from __future__ import annotations

from fastapi.testclient import TestClient

from example_enterprise.main import app


def test_health_family() -> None:
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json().get("status") == "ready"
    status = client.get("/status")
    assert status.status_code == 200
    assert status.json().get("status") in {"healthy", "degraded"}


def test_capabilities_and_feature_flags() -> None:
    client = TestClient(app)
    cap = client.get("/sdk/capabilities")
    assert cap.status_code == 200
    assert "tenant_isolation" in cap.json().get("features", {})
    ff = client.get("/sdk/feature-flags")
    assert ff.status_code == 200
    flags = ff.json().get("flags", {})
    assert flags.get("enterprise_demo") is True


def test_api_ping() -> None:
    response = TestClient(app).get("/api/ping")
    assert response.status_code == 200
    assert response.json() == {"service": "example-enterprise"}


def test_security_hardening_headers_on_response() -> None:
    response = TestClient(app).get("/health")
    assert response.headers.get("x-content-type-options") == "nosniff"
