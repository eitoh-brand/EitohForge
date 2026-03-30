"""Service-layer validation orchestration."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from typing import Any

from eitohforge_sdk.core.validation.context import ValidationContext, ValidationStage
from eitohforge_sdk.core.validation.engine import ValidationEngine
from eitohforge_sdk.core.validation.errors import ValidationResult
from eitohforge_sdk.core.validation.hooks import BusinessValidationHook, SecurityValidationHook


class ServiceValidationHooks:
    """Enforce business and security validation in application services."""

    def __init__(
        self,
        *,
        business_hooks: Iterable[BusinessValidationHook] = (),
        security_hooks: Iterable[SecurityValidationHook] = (),
    ) -> None:
        self._business_engine = ValidationEngine()
        self._security_engine = ValidationEngine()
        self.register_business_hooks(business_hooks)
        self.register_security_hooks(security_hooks)

    def register_business_hook(self, hook: BusinessValidationHook) -> None:
        self._business_engine.register(hook)

    def register_business_hooks(self, hooks: Iterable[BusinessValidationHook]) -> None:
        self._business_engine.register_many(hooks)

    def register_security_hook(self, hook: SecurityValidationHook) -> None:
        self._security_engine.register(hook)

    def register_security_hooks(self, hooks: Iterable[SecurityValidationHook]) -> None:
        self._security_engine.register_many(hooks)

    async def validate_business(
        self, payload: Any, context: ValidationContext, *, stop_on_first_error: bool = False
    ) -> ValidationResult:
        business_context = replace(context, stage=ValidationStage.BUSINESS)
        return await self._business_engine.validate(
            payload, business_context, stop_on_first_error=stop_on_first_error
        )

    async def validate_security(
        self, payload: Any, context: ValidationContext, *, stop_on_first_error: bool = False
    ) -> ValidationResult:
        security_context = replace(context, stage=ValidationStage.SECURITY)
        return await self._security_engine.validate(
            payload, security_context, stop_on_first_error=stop_on_first_error
        )

    async def validate_or_raise(
        self, payload: Any, context: ValidationContext, *, stop_on_first_error: bool = False
    ) -> None:
        business_context = replace(context, stage=ValidationStage.BUSINESS)
        security_context = replace(context, stage=ValidationStage.SECURITY)
        await self._business_engine.validate_or_raise(
            payload, business_context, stop_on_first_error=stop_on_first_error
        )
        await self._security_engine.validate_or_raise(
            payload, security_context, stop_on_first_error=stop_on_first_error
        )

