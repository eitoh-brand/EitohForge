"""Unified security context model and request lifecycle helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request


@dataclass(frozen=True)
class SecurityContext:
    """Unified security context extracted from incoming request metadata."""

    actor_id: str | None
    tenant_id: str | None
    roles: tuple[str, ...]
    permissions: tuple[str, ...]
    request_id: str | None
    trace_id: str | None
    session_id: str | None


def build_security_context_from_headers(headers: Mapping[str, str]) -> SecurityContext:
    """Build a context from standard request headers."""
    return SecurityContext(
        actor_id=headers.get("x-actor-id"),
        tenant_id=headers.get("x-tenant-id"),
        roles=_parse_csv_values(headers.get("x-roles")),
        permissions=_parse_csv_values(headers.get("x-permissions")),
        request_id=headers.get("x-request-id"),
        trace_id=headers.get("x-trace-id"),
        session_id=headers.get("x-session-id"),
    )


def get_request_security_context(request: Request) -> SecurityContext:
    """Get context from request state, or lazily build and cache it."""
    existing = getattr(request.state, "security_context", None)
    if isinstance(existing, SecurityContext):
        return existing
    context = build_security_context_from_headers(request.headers)
    request.state.security_context = context
    return context


def register_security_context_middleware(app: FastAPI) -> None:
    """Attach security context to request state for every request."""

    @app.middleware("http")
    async def _security_context_middleware(request: Request, call_next: Any) -> Any:
        request.state.security_context = build_security_context_from_headers(request.headers)
        return await call_next(request)


def _parse_csv_values(raw_value: str | None) -> tuple[str, ...]:
    if raw_value is None:
        return ()
    values = tuple(part.strip().lower() for part in raw_value.split(",") if part.strip())
    return values

