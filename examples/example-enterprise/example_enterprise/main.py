"""FastAPI app wiring core EitohForge middleware and platform endpoints."""

from __future__ import annotations

from fastapi import FastAPI

from eitohforge_sdk.core import (
    FeatureFlagDefinition,
    FeatureFlagService,
    ForgeAppBuildConfig,
    build_forge_app,
)
from eitohforge_sdk.core.config import get_settings

_feature_flag_service = FeatureFlagService()
_feature_flag_service.register(
    FeatureFlagDefinition(key="enterprise_demo", enabled=True, rollout_percentage=100)
)


def create_app() -> FastAPI:
    app = build_forge_app(
        build=ForgeAppBuildConfig(
            title="Example Enterprise",
            feature_flag_service=_feature_flag_service,
            settings_provider=get_settings,
        )
    )

    @app.get("/api/ping")
    def api_ping() -> dict[str, str]:
        return {"service": "example-enterprise"}

    return app


app = create_app()
