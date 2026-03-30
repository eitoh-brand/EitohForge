from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from eitohforge_sdk.core.capabilities import build_capability_profile, register_capabilities_endpoint
from eitohforge_sdk.core.config import (
    AppSettings,
    AuthSettings,
    IdempotencySettings,
    RateLimitSettings,
    RequestSigningSettings,
    SearchSettings,
)


def test_build_capability_profile_reflects_runtime_settings() -> None:
    settings = AppSettings(
        app_name="forge-service",
        app_env="dev",
        auth=AuthSettings(jwt_secret="dev-secret-value-at-least-32-characters"),
        rate_limit=RateLimitSettings(enabled=False),
        idempotency=IdempotencySettings(enabled=True),
        request_signing=RequestSigningSettings(
            enabled=True,
            shared_secret="super-secret-value",
            methods="POST,PUT",
        ),
        search=SearchSettings(enabled=True, provider="memory", index_prefix="forge"),
    )

    profile = build_capability_profile(settings)
    assert profile["app_name"] == "forge-service"
    assert profile["app_env"] == "dev"
    assert profile["features"]["rate_limit"] is False
    assert profile["features"]["idempotency"] is True
    assert profile["features"]["request_signing"] is True
    assert profile["features"]["search_integration"] is True
    assert profile["features"]["tenant_isolation"] is True
    assert profile["features"]["feature_flags"] is True
    assert profile["features"]["security_hardening"] is True
    assert profile["request_signing"]["methods"] == ("POST", "PUT")
    assert profile["providers"]["search"] == "memory"
    assert profile["search"]["index_prefix"] == "forge"
    assert profile["feature_flags"]["endpoint_path"] == "/sdk/feature-flags"
    assert profile["security_hardening"]["max_request_bytes"] == 2097152


def test_register_capabilities_endpoint_serves_profile() -> None:
    app = FastAPI()
    settings = AppSettings(
        app_name="mobile-service",
        request_signing=RequestSigningSettings(
            enabled=True,
            shared_secret="signed-secret",
        ),
    )
    register_capabilities_endpoint(app, settings_provider=lambda: settings)

    client = TestClient(app)
    response = client.get("/sdk/capabilities")
    assert response.status_code == 200
    payload = response.json()
    assert payload["app_name"] == "mobile-service"
    assert payload["request_signing"]["enabled"] is True
    assert payload["providers"]["cache"] == settings.cache.provider

