from __future__ import annotations

import asyncio

import pytest

from eitohforge_sdk.application.services import ServiceValidationHooks
from eitohforge_sdk.core.validation import (
    AuthenticatedActorSecurityHook,
    PermissionSecurityHook,
    TenantScopeBusinessHook,
    ValidationContext,
    ValidationFailedError,
    ValidationStage,
)


def _build_service_hooks() -> ServiceValidationHooks:
    return ServiceValidationHooks(
        business_hooks=(TenantScopeBusinessHook(),),
        security_hooks=(
            AuthenticatedActorSecurityHook(),
            PermissionSecurityHook(required_permissions=("users:write",)),
        ),
    )


def test_service_validation_hooks_raise_for_tenant_scope_mismatch() -> None:
    hooks = _build_service_hooks()
    with pytest.raises(ValidationFailedError):
        asyncio.run(
            hooks.validate_or_raise(
                {"tenant_id": "tenant-b"},
                ValidationContext(
                    stage=ValidationStage.REQUEST,
                    actor_id="actor-1",
                    tenant_id="tenant-a",
                    metadata={"permissions": ("users:write",)},
                ),
            )
        )


def test_service_validation_hooks_raise_for_missing_actor() -> None:
    hooks = _build_service_hooks()
    with pytest.raises(ValidationFailedError):
        asyncio.run(
            hooks.validate_or_raise(
                {"tenant_id": "tenant-a"},
                ValidationContext(
                    stage=ValidationStage.REQUEST,
                    actor_id=None,
                    tenant_id="tenant-a",
                    metadata={"permissions": ("users:write",)},
                ),
            )
        )


def test_service_validation_hooks_raise_for_missing_permission() -> None:
    hooks = _build_service_hooks()
    with pytest.raises(ValidationFailedError):
        asyncio.run(
            hooks.validate_or_raise(
                {"tenant_id": "tenant-a"},
                ValidationContext(
                    stage=ValidationStage.REQUEST,
                    actor_id="actor-1",
                    tenant_id="tenant-a",
                    metadata={"permissions": ("users:read",)},
                ),
            )
        )


def test_service_validation_hooks_pass_for_valid_context() -> None:
    hooks = _build_service_hooks()
    asyncio.run(
        hooks.validate_or_raise(
            {"tenant_id": "tenant-a"},
            ValidationContext(
                stage=ValidationStage.REQUEST,
                actor_id="actor-1",
                tenant_id="tenant-a",
                metadata={"permissions": ("users:read", "users:write")},
            ),
        )
    )

