from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from eitohforge_sdk.core.api_version_deprecation import register_api_version_deprecation_middleware
from eitohforge_sdk.core.config import ApiVersioningSettings, AppSettings, AuthSettings


def test_v1_deprecation_headers_applied_when_enabled() -> None:
    settings = AppSettings(
        auth=AuthSettings(jwt_secret="unit-test-secret-value-at-least-32-chars"),
        api_versioning=ApiVersioningSettings(
            deprecate_v1=True,
            v1_sunset_http_date="Sat, 01 Jan 2030 00:00:00 GMT",
            v1_link_deprecation="https://docs.example.com/v1-deprecation",
        ),
    )
    app = FastAPI()

    @app.get("/v1/ping")
    def v1_ping() -> dict[str, str]:
        return {"v": "1"}

    @app.get("/other/ping")
    def other_ping() -> dict[str, str]:
        return {"v": "x"}

    register_api_version_deprecation_middleware(app, settings_provider=lambda: settings)
    client = TestClient(app)
    r1 = client.get("/v1/ping")
    assert r1.headers.get("Deprecation") == "true"
    assert r1.headers.get("Sunset") == "Sat, 01 Jan 2030 00:00:00 GMT"
    assert "rel=\"deprecation\"" in (r1.headers.get("Link") or "")
    r2 = client.get("/other/ping")
    assert r2.headers.get("Deprecation") is None


def test_v1_deprecation_middleware_noop_when_disabled() -> None:
    settings = AppSettings(
        auth=AuthSettings(jwt_secret="unit-test-secret-value-at-least-32-chars"),
        api_versioning=ApiVersioningSettings(deprecate_v1=False),
    )
    app = FastAPI()

    @app.get("/v1/ping")
    def v1_ping() -> dict[str, str]:
        return {"v": "1"}

    register_api_version_deprecation_middleware(app, settings_provider=lambda: settings)
    client = TestClient(app)
    r = client.get("/v1/ping")
    assert r.headers.get("Deprecation") is None
