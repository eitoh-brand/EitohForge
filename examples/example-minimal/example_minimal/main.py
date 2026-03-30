"""Minimal FastAPI app: health + SDK capabilities endpoint."""

from __future__ import annotations

from fastapi import FastAPI

from eitohforge_sdk.core.capabilities import register_capabilities_endpoint
from eitohforge_sdk.core.config import get_settings


def create_app() -> FastAPI:
    app = FastAPI(title="Example Minimal")
    register_capabilities_endpoint(app, settings_provider=get_settings)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
