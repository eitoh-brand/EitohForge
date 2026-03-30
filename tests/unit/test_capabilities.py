from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from eitohforge_sdk.core.capabilities import build_capability_profile, register_capabilities_endpoint
from eitohforge_sdk.core.config import (
    AppSettings,
    AuthSettings,
    IdempotencySettings,
    RateLimitSettings,
    RealtimeSettings,
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
    assert profile["features"]["realtime_websocket"] is True
    assert profile["request_signing"]["methods"] == ("POST", "PUT")
    assert profile["providers"]["search"] == "memory"
    assert profile["search"]["index_prefix"] == "forge"
    assert profile["feature_flags"]["endpoint_path"] == "/sdk/feature-flags"
    assert profile["security_hardening"]["max_request_bytes"] == 2097152
    assert profile["deployment"]["profile"] == "dev"
    assert profile["deployment"]["expose_detailed_errors"] is True
    assert profile["runtime"]["cors_enabled"] is False
    assert profile["sdk_feature_catalog_meta"]["feature_area_count"] >= 1
    assert isinstance(profile["sdk_feature_catalog"], list)
    assert any(row.get("key") == "config" for row in profile["sdk_feature_catalog"])
    assert profile["realtime"]["enabled"] is True
    assert profile["realtime"]["websocket_path"] == "/realtime/ws"
    assert profile["realtime"]["require_access_jwt"] is True
    assert profile["realtime"]["hub_kind"] == "in_memory"
    assert profile["realtime"]["direct_to_actor_supported"] is True
    assert profile["auth"]["jwt_enabled"] is True
    assert profile["runtime"]["enforce_https_redirect"] is False
    assert profile["tenant"]["tenant_context_current_available"] is True
    assert "tenant_id" in profile["tenant"]["tenant_context_current_fields"]


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


def test_capability_profile_realtime_hub_kind_redis_when_url_set() -> None:
    settings = AppSettings(
        auth=AuthSettings(jwt_secret="dev-secret-value-at-least-32-characters"),
        rate_limit=RateLimitSettings(enabled=False),
        realtime=RealtimeSettings(enabled=True, redis_url="redis://127.0.0.1:6379/0"),
    )
    profile = build_capability_profile(settings)
    assert profile["realtime"]["hub_kind"] == "redis_fanout"

