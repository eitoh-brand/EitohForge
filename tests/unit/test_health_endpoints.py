from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from eitohforge_sdk.core.config import AppSettings, AuthSettings
from eitohforge_sdk.core.health import register_health_endpoints


def test_health_endpoints_expose_health_ready_status() -> None:
    app = FastAPI()
    register_health_endpoints(
        app,
        checks={"db": lambda: True, "cache": lambda: False},
        settings_provider=lambda: AppSettings(
            app_name="forge",
            app_env="dev",
            auth=AuthSettings(jwt_secret="dev-secret-value-at-least-32-characters"),
        ),
    )

    client = TestClient(app)
    health = client.get("/health")
    ready = client.get("/ready")
    status = client.get("/status")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.json()["status"] == "not_ready"
    assert status.status_code == 200
    payload = status.json()
    assert payload["status"] == "degraded"
    assert payload["service"] == {"name": "forge", "env": "dev"}
    assert len(payload["checks"]) == 2

