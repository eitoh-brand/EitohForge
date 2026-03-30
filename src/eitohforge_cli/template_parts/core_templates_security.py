"""Security core template fragments."""

CORE_SECURITY_FILE_TEMPLATES: dict[str, str] = {
    'app/core/abac.py': """from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import wraps
import inspect
from typing import Any, ParamSpec, Protocol, TypeVar, cast

from fastapi import Request

from app.core.security import SecurityPrincipal, principal_from_context
from app.core.security_context import get_request_security_context


class PolicyDeniedError(PermissionError):
    pass


@dataclass(frozen=True)
class PolicyContext:
    principal: SecurityPrincipal
    attributes: Mapping[str, Any]


class AccessPolicy(Protocol):
    name: str

    def evaluate(self, context: PolicyContext) -> bool:
        ...


@dataclass(frozen=True)
class ActorPresentPolicy:
    name: str = "actor_present"

    def evaluate(self, context: PolicyContext) -> bool:
        return context.principal.actor_id is not None


@dataclass(frozen=True)
class TenantMatchPolicy:
    resource_tenant_attr: str = "resource_tenant_id"
    name: str = "tenant_match"

    def evaluate(self, context: PolicyContext) -> bool:
        principal_tenant = context.principal.tenant_id
        if principal_tenant is None:
            return False
        resource_tenant = context.attributes.get(self.resource_tenant_attr)
        if resource_tenant is None:
            return False
        return str(resource_tenant) == principal_tenant


class PolicyEngine:
    def evaluate(self, context: PolicyContext, policies: tuple[AccessPolicy, ...]) -> tuple[str, ...]:
        return tuple(policy.name for policy in policies if not policy.evaluate(context))

    def assert_allowed(self, context: PolicyContext, policies: tuple[AccessPolicy, ...]) -> None:
        denied = self.evaluate(context, policies)
        if denied:
            raise PolicyDeniedError(f"ABAC denied by policies: {', '.join(denied)}")


def attributes_from_request(request: Request) -> dict[str, Any]:
    attributes: dict[str, Any] = dict(request.path_params)
    attributes.update(dict(request.query_params.items()))
    resource_tenant = request.headers.get("x-resource-tenant-id")
    if resource_tenant is not None:
        attributes["resource_tenant_id"] = resource_tenant
    return attributes


def require_policies(*policies: AccessPolicy) -> Callable[[Request], Any]:
    engine = PolicyEngine()

    async def _dependency(request: Request) -> PolicyContext:
        security_context = get_request_security_context(request)
        principal = principal_from_context(security_context)
        attributes = attributes_from_request(request)
        if security_context.tenant_id is not None and "resource_tenant_id" not in attributes:
            attributes["resource_tenant_id"] = security_context.tenant_id
        context = PolicyContext(principal=principal, attributes=attributes)
        engine.assert_allowed(context, policies)
        return context

    return _dependency


P = ParamSpec("P")
R = TypeVar("R")
RAsync = TypeVar("RAsync")


def abac_required(*policies: AccessPolicy) -> Callable[[Callable[P, R]], Callable[P, R]]:
    engine = PolicyEngine()

    def _decorator(func: Callable[P, R]) -> Callable[P, R]:
        if inspect.iscoroutinefunction(func):
            async_func = cast(Callable[P, Any], func)

            @wraps(func)
            async def _async_wrapper(*args: P.args, **kwargs: P.kwargs) -> RAsync:
                principal = kwargs.get("principal")
                attributes = kwargs.get("attributes")
                if not isinstance(principal, SecurityPrincipal):
                    raise PolicyDeniedError("Missing `principal` for ABAC-protected function.")
                if not isinstance(attributes, Mapping):
                    raise PolicyDeniedError("Missing `attributes` for ABAC-protected function.")
                engine.assert_allowed(PolicyContext(principal=principal, attributes=attributes), policies)
                return await async_func(*args, **kwargs)

            return cast(Callable[P, R], _async_wrapper)

        @wraps(func)
        def _sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            principal = kwargs.get("principal")
            attributes = kwargs.get("attributes")
            if not isinstance(principal, SecurityPrincipal):
                raise PolicyDeniedError("Missing `principal` for ABAC-protected function.")
            if not isinstance(attributes, Mapping):
                raise PolicyDeniedError("Missing `attributes` for ABAC-protected function.")
            engine.assert_allowed(PolicyContext(principal=principal, attributes=attributes), policies)
            return func(*args, **kwargs)

        return _sync_wrapper

    return _decorator
""",
    'app/core/security_context.py': """from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request


@dataclass(frozen=True)
class SecurityContext:
    actor_id: str | None
    tenant_id: str | None
    roles: tuple[str, ...]
    permissions: tuple[str, ...]
    request_id: str | None
    trace_id: str | None
    session_id: str | None


def build_security_context_from_headers(headers: Mapping[str, str]) -> SecurityContext:
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
    existing = getattr(request.state, "security_context", None)
    if isinstance(existing, SecurityContext):
        return existing
    context = build_security_context_from_headers(request.headers)
    request.state.security_context = context
    return context


def register_security_context_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def _security_context_middleware(request: Request, call_next: Any) -> Any:
        request.state.security_context = build_security_context_from_headers(request.headers)
        return await call_next(request)


def _parse_csv_values(raw_value: str | None) -> tuple[str, ...]:
    if raw_value is None:
        return ()
    return tuple(part.strip().lower() for part in raw_value.split(",") if part.strip())
""",
    'app/core/security.py': """from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import wraps
import inspect
from typing import Any, ParamSpec, TypeVar, cast

from fastapi import Request


class RoleDeniedError(PermissionError):
    pass


@dataclass(frozen=True)
class SecurityPrincipal:
    actor_id: str | None
    roles: tuple[str, ...]
    tenant_id: str | None = None


def parse_roles(raw_roles: str | None) -> tuple[str, ...]:
    if raw_roles is None:
        return ()
    return tuple(part.strip().lower() for part in raw_roles.split(",") if part.strip())


def principal_from_headers(headers: Mapping[str, str]) -> SecurityPrincipal:
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
    return SecurityPrincipal(actor_id=context.actor_id, roles=context.roles, tenant_id=context.tenant_id)


def assert_roles(principal: SecurityPrincipal, required_roles: tuple[str, ...]) -> None:
    normalized_required = tuple(role.lower() for role in required_roles if role)
    if not normalized_required:
        return
    principal_roles = set(principal.roles)
    if any(required in principal_roles for required in normalized_required):
        return
    required_repr = ", ".join(normalized_required)
    raise RoleDeniedError(f"Missing required role. Need one of: {required_repr}.")


def require_roles(*required_roles: str) -> Callable[[Request], Any]:
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
    def _decorator(func: Callable[P, R]) -> Callable[P, R]:
        if inspect.iscoroutinefunction(func):
            async_func = cast(Callable[P, Any], func)

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
""",
}
