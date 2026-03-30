"""RBAC security helpers and decorators."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from functools import wraps
import inspect
from typing import ParamSpec, TypeVar, cast

from fastapi import Request

from eitohforge_sdk.core.security_context import SecurityContext, get_request_security_context


class RoleDeniedError(PermissionError):
    """Raised when principal does not satisfy role requirements."""


@dataclass(frozen=True)
class SecurityPrincipal:
    """Resolved caller principal for authorization checks."""

    actor_id: str | None
    roles: tuple[str, ...]
    tenant_id: str | None = None


def parse_roles(raw_roles: str | None) -> tuple[str, ...]:
    """Parse comma-separated role header value into normalized role tuple."""
    if raw_roles is None:
        return ()
    values = tuple(part.strip().lower() for part in raw_roles.split(",") if part.strip())
    return values


def principal_from_headers(headers: Mapping[str, str]) -> SecurityPrincipal:
    """Build principal from standard headers."""
    context = SecurityContext(
        actor_id=headers.get("x-actor-id"),
        tenant_id=headers.get("x-tenant-id"),
        roles=parse_roles(headers.get("x-roles")),
        permissions=(),
        request_id=headers.get("x-request-id"),
        trace_id=headers.get("x-trace-id"),
        session_id=headers.get("x-session-id"),
    )
    return principal_from_context(context)


def principal_from_context(context: SecurityContext) -> SecurityPrincipal:
    """Build authorization principal from security context."""
    return SecurityPrincipal(actor_id=context.actor_id, tenant_id=context.tenant_id, roles=context.roles)


def assert_roles(principal: SecurityPrincipal, required_roles: tuple[str, ...]) -> None:
    """Raise when principal does not include at least one required role."""
    normalized_required = tuple(role.lower() for role in required_roles if role)
    if not normalized_required:
        return
    principal_roles = set(principal.roles)
    if any(required in principal_roles for required in normalized_required):
        return
    required_repr = ", ".join(normalized_required)
    raise RoleDeniedError(f"Missing required role. Need one of: {required_repr}.")


def require_roles(*required_roles: str) -> Callable[[Request], Awaitable[SecurityPrincipal]]:
    """FastAPI dependency factory enforcing RBAC from request headers."""

    async def _dependency(request: Request) -> SecurityPrincipal:
        context = get_request_security_context(request)
        principal = principal_from_context(context)
        assert_roles(principal, required_roles)
        return principal

    return _dependency


P = ParamSpec("P")
R = TypeVar("R")
RAsync = TypeVar("RAsync")


def rbac_required(*required_roles: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator enforcing RBAC for callables expecting `principal` kwarg."""

    def _decorator(func: Callable[P, R]) -> Callable[P, R]:
        if inspect.iscoroutinefunction(func):

            async_func = cast(Callable[P, Awaitable[RAsync]], func)

            @wraps(func)
            async def _async_wrapper(*args: P.args, **kwargs: P.kwargs) -> RAsync:
                principal = kwargs.get("principal")
                if not isinstance(principal, SecurityPrincipal):
                    raise RoleDeniedError("Missing `principal` for RBAC-protected function.")
                assert_roles(principal, required_roles)
                return await async_func(*args, **kwargs)

            return cast(Callable[P, R], _async_wrapper)

        @wraps(func)
        def _sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            principal = kwargs.get("principal")
            if not isinstance(principal, SecurityPrincipal):
                raise RoleDeniedError("Missing `principal` for RBAC-protected function.")
            assert_roles(principal, required_roles)
            return func(*args, **kwargs)

        return _sync_wrapper

    return _decorator

