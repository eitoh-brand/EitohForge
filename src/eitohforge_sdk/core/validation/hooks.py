"""Business and security validation hook contracts and defaults."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel

from eitohforge_sdk.core.validation.context import ValidationContext
from eitohforge_sdk.core.validation.errors import ValidationIssue


class BusinessValidationHook(Protocol):
    """Business-layer validation hook contract."""

    name: str

    async def validate(self, payload: Any, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        """Return business validation issues."""


class SecurityValidationHook(Protocol):
    """Security-layer validation hook contract."""

    name: str

    async def validate(self, payload: Any, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        """Return security validation issues."""


@dataclass(frozen=True)
class TenantScopeBusinessHook:
    """Ensure payload tenant scope does not escape request tenant scope."""

    field_name: str = "tenant_id"
    name: str = "tenant-scope-business-hook"

    async def validate(self, payload: Any, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        payload_tenant = _read_field(payload, self.field_name)
        if context.tenant_id is None or payload_tenant is None:
            return ()
        if str(payload_tenant) == context.tenant_id:
            return ()
        return (
            ValidationIssue(
                code="TENANT_SCOPE_VIOLATION",
                message="Payload tenant scope does not match validation context tenant.",
                field=self.field_name,
            ),
        )


@dataclass(frozen=True)
class AuthenticatedActorSecurityHook:
    """Require authenticated actor before protected actions."""

    name: str = "authenticated-actor-security-hook"

    async def validate(self, payload: Any, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        _ = payload
        if context.actor_id is not None:
            return ()
        return (
            ValidationIssue(
                code="AUTH_ACTOR_REQUIRED",
                message="Authenticated actor is required for this operation.",
                field="actor_id",
            ),
        )


@dataclass(frozen=True)
class PermissionSecurityHook:
    """Require one or more permissions from context metadata."""

    required_permissions: tuple[str, ...]
    metadata_key: str = "permissions"
    name: str = "permission-security-hook"

    async def validate(self, payload: Any, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        _ = payload
        raw_permissions = context.metadata.get(self.metadata_key, ())
        available_permissions = _normalize_permissions(raw_permissions)
        missing = tuple(permission for permission in self.required_permissions if permission not in available_permissions)
        if not missing:
            return ()
        missing_values = ", ".join(missing)
        return (
            ValidationIssue(
                code="AUTH_PERMISSION_DENIED",
                message=f"Missing required permissions: {missing_values}.",
                field=self.metadata_key,
            ),
        )


def _normalize_permissions(raw_permissions: Any) -> set[str]:
    if isinstance(raw_permissions, str):
        return {raw_permissions}
    if isinstance(raw_permissions, Iterable):
        values = {str(item) for item in raw_permissions}
        return values
    return set()


def _read_field(payload: Any, field_name: str) -> Any | None:
    if isinstance(payload, BaseModel):
        return payload.model_dump(exclude_unset=True).get(field_name)
    if isinstance(payload, Mapping):
        return payload.get(field_name)
    if hasattr(payload, field_name):
        return getattr(payload, field_name)
    return None

