"""Tenant context helpers and isolation middleware."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from eitohforge_sdk.core.security_context import (
    SecurityContext,
    build_security_context_from_headers,
    get_request_security_context,
)


@dataclass(frozen=True)
class TenantContext:
    """Tenant-scoped request context."""

    tenant_id: str | None
    actor_id: str | None
    request_id: str | None
    trace_id: str | None


@dataclass(frozen=True)
class TenantIsolationRule:
    """Tenant isolation middleware configuration."""

    enabled: bool = True
    required_for_write_methods: bool = True
    write_methods: tuple[str, ...] = ("POST", "PUT", "PATCH", "DELETE")
    scope_path_prefix: str | None = None
    resource_tenant_header: str = "x-resource-tenant-id"


class TenantIsolationError(PermissionError):
    """Raised when tenant isolation constraints fail."""


def build_tenant_context_from_security_context(context: SecurityContext) -> TenantContext:
    """Build tenant context from security context."""
    return TenantContext(
        tenant_id=context.tenant_id,
        actor_id=context.actor_id,
        request_id=context.request_id,
        trace_id=context.trace_id,
    )


def build_tenant_context_from_headers(headers: dict[str, str]) -> TenantContext:
    """Build tenant context from request headers."""
    return build_tenant_context_from_security_context(build_security_context_from_headers(headers))


def get_request_tenant_context(request: Request) -> TenantContext:
    """Get tenant context from request state, lazily building if missing."""
    existing = getattr(request.state, "tenant_context", None)
    if isinstance(existing, TenantContext):
        return existing
    context = build_tenant_context_from_security_context(get_request_security_context(request))
    request.state.tenant_context = context
    return context


def assert_tenant_access(
    tenant_context: TenantContext,
    *,
    resource_tenant_id: str | None,
) -> None:
    """Ensure request tenant matches requested resource tenant boundary."""
    if resource_tenant_id is None or not resource_tenant_id.strip():
        return
    if tenant_context.tenant_id is None:
        raise TenantIsolationError("Tenant context is missing for tenant-scoped resource access.")
    if tenant_context.tenant_id != resource_tenant_id.strip():
        raise TenantIsolationError("Cross-tenant access denied.")


def register_tenant_context_middleware(
    app: FastAPI,
    rule: TenantIsolationRule,
) -> None:
    """Register middleware to enforce tenant boundary checks."""

    @app.middleware("http")
    async def _tenant_context_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not rule.enabled:
            return await call_next(request)

        if rule.scope_path_prefix is not None and not request.url.path.startswith(rule.scope_path_prefix):
            return await call_next(request)

        tenant_context = build_tenant_context_from_security_context(get_request_security_context(request))
        request.state.tenant_context = tenant_context

        method = request.method.upper()
        if rule.required_for_write_methods and method in set(rule.write_methods) and not tenant_context.tenant_id:
            return _tenant_error("TENANT_CONTEXT_REQUIRED", "Tenant context is required for write operations.")

        try:
            assert_tenant_access(
                tenant_context,
                resource_tenant_id=request.headers.get(rule.resource_tenant_header),
            )
        except TenantIsolationError:
            return _tenant_error("TENANT_ACCESS_DENIED", "Tenant boundary violation.")

        return await call_next(request)


def _tenant_error(code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=403, content={"success": False, "error": {"code": code, "message": message}})
