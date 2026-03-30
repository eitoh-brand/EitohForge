"""ABAC policy engine, dependencies, and decorators."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import wraps
import inspect
from typing import Any, Awaitable, ParamSpec, Protocol, TypeVar, cast

from fastapi import Request

from eitohforge_sdk.core.security import SecurityPrincipal, principal_from_context
from eitohforge_sdk.core.security_context import get_request_security_context


class PolicyDeniedError(PermissionError):
    """Raised when one or more ABAC policies deny access."""


@dataclass(frozen=True)
class PolicyContext:
    """Evaluation context for ABAC policies."""

    principal: SecurityPrincipal
    attributes: Mapping[str, Any]


class AccessPolicy(Protocol):
    """ABAC policy contract."""

    name: str

    def evaluate(self, context: PolicyContext) -> bool:
        ...


@dataclass(frozen=True)
class ActorPresentPolicy:
    """Require an authenticated actor."""

    name: str = "actor_present"

    def evaluate(self, context: PolicyContext) -> bool:
        return context.principal.actor_id is not None


@dataclass(frozen=True)
class TenantMatchPolicy:
    """Require principal tenant to match resource tenant."""

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
    """ABAC policy evaluation engine."""

    def evaluate(self, context: PolicyContext, policies: tuple[AccessPolicy, ...]) -> tuple[str, ...]:
        denied = tuple(policy.name for policy in policies if not policy.evaluate(context))
        return denied

    def assert_allowed(self, context: PolicyContext, policies: tuple[AccessPolicy, ...]) -> None:
        denied = self.evaluate(context, policies)
        if denied:
            raise PolicyDeniedError(f"ABAC denied by policies: {', '.join(denied)}")


def attributes_from_request(request: Request) -> dict[str, Any]:
    """Extract ABAC attributes from path/query/headers."""
    attributes: dict[str, Any] = dict(request.path_params)
    attributes.update(dict(request.query_params.items()))
    resource_tenant = request.headers.get("x-resource-tenant-id")
    if resource_tenant is not None:
        attributes["resource_tenant_id"] = resource_tenant
    return attributes


def require_policies(*policies: AccessPolicy) -> Callable[[Request], Awaitable[PolicyContext]]:
    """FastAPI dependency enforcing ABAC policies."""
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
    """Decorator enforcing ABAC for functions requiring `principal` and `attributes` kwargs."""
    engine = PolicyEngine()

    def _decorator(func: Callable[P, R]) -> Callable[P, R]:
        if inspect.iscoroutinefunction(func):
            async_func = cast(Callable[P, Awaitable[RAsync]], func)

            @wraps(func)
            async def _async_wrapper(*args: P.args, **kwargs: P.kwargs) -> RAsync:
                principal = kwargs.get("principal")
                attributes = kwargs.get("attributes")
                if not isinstance(principal, SecurityPrincipal):
                    raise PolicyDeniedError("Missing `principal` for ABAC-protected function.")
                if not isinstance(attributes, Mapping):
                    raise PolicyDeniedError("Missing `attributes` for ABAC-protected function.")
                context = PolicyContext(principal=principal, attributes=attributes)
                engine.assert_allowed(context, policies)
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
            context = PolicyContext(principal=principal, attributes=attributes)
            engine.assert_allowed(context, policies)
            return func(*args, **kwargs)

        return _sync_wrapper

    return _decorator

