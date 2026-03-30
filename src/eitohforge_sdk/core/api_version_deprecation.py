"""HTTP deprecation headers for versioned API routes (RFC 9745 style)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from eitohforge_sdk.core.config import AppSettings


def register_api_version_deprecation_middleware(
    app: FastAPI, *, settings_provider: Callable[[], AppSettings]
) -> None:
    """Add ``Deprecation`` / ``Sunset`` / ``Link`` response headers for paths under ``/v1``.

    Controlled by ``AppSettings.api_versioning``. No-op when ``deprecate_v1`` is false.
    """

    @app.middleware("http")
    async def _apply_v1_deprecation_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        settings = settings_provider()
        cfg = settings.api_versioning
        if not cfg.deprecate_v1:
            return response
        path = request.scope.get("path") or ""
        if not (path == "/v1" or path.startswith("/v1/")):
            return response
        response.headers["Deprecation"] = "true"
        if cfg.v1_sunset_http_date:
            response.headers["Sunset"] = cfg.v1_sunset_http_date
        if cfg.v1_link_deprecation:
            response.headers["Link"] = f'<{cfg.v1_link_deprecation}>; rel="deprecation"'
        return response
