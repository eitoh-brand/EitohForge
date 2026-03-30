"""Security hardening middleware and headers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response


@dataclass(frozen=True)
class SecurityHardeningRule:
    """Security hardening controls for inbound HTTP requests."""

    enabled: bool = True
    max_request_bytes: int = 2_097_152
    allowed_hosts: tuple[str, ...] = ("*",)
    add_security_headers: bool = True
    security_headers: dict[str, str] = field(
        default_factory=lambda: {
            "x-content-type-options": "nosniff",
            "x-frame-options": "DENY",
            "referrer-policy": "no-referrer",
            "x-permitted-cross-domain-policies": "none",
            "content-security-policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        }
    )


def register_security_hardening_middleware(app: FastAPI, rule: SecurityHardeningRule) -> None:
    """Register middleware enforcing request and response hardening policies."""

    @app.middleware("http")
    async def _security_hardening_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not rule.enabled:
            return await call_next(request)

        if not _is_host_allowed(request, rule.allowed_hosts):
            return _hardening_error("HOST_NOT_ALLOWED", "Request host is not allowed.")

        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > rule.max_request_bytes:
            return _hardening_error("REQUEST_ENTITY_TOO_LARGE", "Request body exceeds allowed size.", status_code=413)

        response = await call_next(request)
        if rule.add_security_headers:
            for key, value in rule.security_headers.items():
                response.headers[key] = value
        return response


def _is_host_allowed(request: Request, allowed_hosts: tuple[str, ...]) -> bool:
    normalized = tuple(host.strip().lower() for host in allowed_hosts if host.strip())
    if not normalized or "*" in normalized:
        return True
    host_header = (request.headers.get("host") or "").split(":")[0].lower().strip()
    return host_header in set(normalized)


def _hardening_error(code: str, message: str, *, status_code: int = 400) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"success": False, "error": {"code": code, "message": message}})
