from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from eitohforge_sdk.core.config import AppSettings, AuthSettings, RuntimeSettings
from eitohforge_sdk.core.forge_application import ForgeAppBuildConfig, build_forge_app
from eitohforge_sdk.core.forge_toggles import ForgePlatformToggles
from eitohforge_sdk.infrastructure.sockets.redis_hub import RedisFanoutSocketHub


def test_build_forge_app_minimal_when_middleware_disabled() -> None:
    app = build_forge_app(
        build=ForgeAppBuildConfig(
            title="Bare",
            wire_platform_middleware=False,
            wire_health_family=False,
            wire_capabilities=False,
            wire_feature_flags=False,
            wire_realtime_websocket=False,
        )
    )
    assert isinstance(app, FastAPI)
    assert app.title == "Bare"


def test_build_forge_app_wires_health_and_capabilities() -> None:
    settings = AppSettings(
        auth=AuthSettings(jwt_secret="unit-test-secret-value-at-least-32-chars"),
        rate_limit={"enabled": False},
        audit={"enabled": False},
        observability={"enabled": False},
        idempotency={"enabled": False},
        request_signing={"enabled": False},
        tenant={"enabled": False},
        security_hardening={"enabled": False},
        realtime={"enabled": False},
    )

    app = build_forge_app(
        build=ForgeAppBuildConfig(
            wire_feature_flags=False,
            wire_realtime_websocket=False,
            settings_provider=lambda: settings,
        )
    )
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    cap = client.get("/sdk/capabilities").json()
    assert cap["app_name"] == settings.app_name


def test_build_forge_app_cors_when_runtime_origins_set() -> None:
    settings = AppSettings(
        auth=AuthSettings(jwt_secret="unit-test-secret-value-at-least-32-chars"),
        runtime=RuntimeSettings(cors_allow_origins="http://localhost:3000"),
        rate_limit={"enabled": False},
        audit={"enabled": False},
        observability={"enabled": False},
        idempotency={"enabled": False},
        request_signing={"enabled": False},
        tenant={"enabled": False},
        security_hardening={"enabled": False},
        realtime={"enabled": False},
    )
    app = build_forge_app(
        build=ForgeAppBuildConfig(
            wire_platform_middleware=False,
            wire_health_family=False,
            wire_capabilities=False,
            wire_feature_flags=False,
            wire_realtime_websocket=False,
            settings_provider=lambda: settings,
        )
    )
    assert any(isinstance(m, Middleware) and m.cls is CORSMiddleware for m in app.user_middleware)


def test_build_forge_app_platform_toggle_forces_rate_limit_off() -> None:
    settings = AppSettings(
        auth=AuthSettings(jwt_secret="unit-test-secret-value-at-least-32-chars"),
        realtime={"enabled": False},
    )
    app = build_forge_app(
        build=ForgeAppBuildConfig(
            toggles=ForgePlatformToggles(rate_limit=False),
            wire_feature_flags=False,
            wire_realtime_websocket=False,
            settings_provider=lambda: settings,
        )
    )
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/health" in paths


def test_build_forge_app_registers_realtime_when_enabled() -> None:
    settings = AppSettings(
        auth=AuthSettings(jwt_secret="unit-test-secret-value-at-least-32-chars"),
        rate_limit={"enabled": False},
        audit={"enabled": False},
        observability={"enabled": False},
        idempotency={"enabled": False},
        tenant={"enabled": False},
        security_hardening={"enabled": False},
        realtime={"enabled": True},
    )
    app = build_forge_app(
        build=ForgeAppBuildConfig(
            wire_feature_flags=False,
            settings_provider=lambda: settings,
        )
    )
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/realtime/ws" in paths


def test_build_forge_app_uses_redis_fanout_hub_when_realtime_redis_url_set() -> None:
    settings = AppSettings(
        auth=AuthSettings(jwt_secret="unit-test-secret-value-at-least-32-chars"),
        rate_limit={"enabled": False},
        audit={"enabled": False},
        observability={"enabled": False},
        idempotency={"enabled": False},
        tenant={"enabled": False},
        security_hardening={"enabled": False},
        realtime={"enabled": True, "redis_url": "redis://127.0.0.1:6379/0"},
    )
    app = build_forge_app(
        build=ForgeAppBuildConfig(
            wire_feature_flags=False,
            settings_provider=lambda: settings,
        )
    )
    assert isinstance(app.state.socket_hub, RedisFanoutSocketHub)
    asyncio.run(app.state.socket_hub.aclose())
