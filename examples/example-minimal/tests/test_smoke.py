"""Smoke tests for example-minimal."""

from __future__ import annotations

from fastapi.testclient import TestClient

from example_minimal.main import app


def test_health() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_capabilities_contract() -> None:
    response = TestClient(app).get("/sdk/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body.get("app_name")
    assert isinstance(body.get("features"), dict)
