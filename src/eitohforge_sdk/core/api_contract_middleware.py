"""Optional middleware enforcing the unified JSON envelope (`success` + payload or `error`)."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


@dataclass(frozen=True)
class ApiContractRule:
    """Rules for JSON response envelope validation."""

    enabled: bool = True
    exclude_path_prefixes: tuple[str, ...] = (
        "/docs",
        "/openapi",
        "/redoc",
        "/health",
        "/ready",
        "/status",
        "/metrics",
        "/sdk/capabilities",
    )


def register_api_contract_middleware(
    app: FastAPI,
    *,
    rule: ApiContractRule | None = None,
) -> None:
    """Register middleware that validates JSON bodies for `ApiResponse` / `ApiErrorResponse` shape."""
    resolved = rule or ApiContractRule()
    if not resolved.enabled:
        return

    app.add_middleware(
        _ApiContractEnvelopeMiddleware,
        enforce_rule=resolved,
    )


class _ApiContractEnvelopeMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: object,
        *,
        enforce_rule: ApiContractRule,
    ) -> None:
        super().__init__(app)
        self._rule = enforce_rule

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        if response.status_code == 204:
            return response
        path = request.url.path
        if any(path.startswith(prefix) for prefix in self._rule.exclude_path_prefixes):
            return response
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        try:
            payload = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response(
                content=body,
                status_code=response.status_code,
                headers=_strip_content_length(dict(response.headers)),
                media_type=response.media_type,
            )

        err = _validate_envelope(payload)
        if err is not None:
            return Response(
                content=json.dumps(
                    {
                        "success": False,
                        "error": {
                            "code": "INVALID_API_ENVELOPE",
                            "message": err,
                        },
                    }
                ).encode("utf-8"),
                status_code=500,
                media_type="application/json",
            )

        out = json.dumps(payload).encode("utf-8")
        return Response(
            content=out,
            status_code=response.status_code,
            headers=_strip_content_length(dict(response.headers)),
            media_type="application/json",
        )


def _strip_content_length(headers: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in headers.items() if k.lower() != "content-length"}


def _validate_envelope(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return "JSON root must be an object."
    if "success" not in payload:
        return "Missing boolean `success` field."
    if not isinstance(payload["success"], bool):
        return "`success` must be a boolean."
    if payload["success"] is False:
        err = payload.get("error")
        if not isinstance(err, dict):
            return "When success is false, `error` must be an object."
        if "code" not in err or "message" not in err:
            return "`error` must include string fields `code` and `message`."
        return None
    return None
