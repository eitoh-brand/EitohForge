"""Validation orchestration engine."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from eitohforge_sdk.core.validation.context import ValidationContext
from eitohforge_sdk.core.validation.contracts import ValidationRule
from eitohforge_sdk.core.validation.errors import ValidationFailedError, ValidationIssue, ValidationResult


class ValidationEngine:
    """Rule orchestration entrypoint for layered validation."""

    def __init__(self) -> None:
        self._rules: list[ValidationRule[Any]] = []

    def register(self, rule: ValidationRule[Any]) -> None:
        """Register a validation rule in execution order."""
        self._rules.append(rule)

    def register_many(self, rules: Iterable[ValidationRule[Any]]) -> None:
        """Register multiple rules preserving order."""
        for rule in rules:
            self.register(rule)

    async def validate(
        self,
        payload: Any,
        context: ValidationContext,
        *,
        stop_on_first_error: bool = False,
    ) -> ValidationResult:
        """Execute validation rules and return aggregate result."""
        issues: list[ValidationIssue] = []
        for rule in self._rules:
            rule_issues = await rule.validate(payload, context)
            issues.extend(rule_issues)
            if stop_on_first_error and any(issue.severity.value == "error" for issue in rule_issues):
                break
        return ValidationResult(issues=tuple(issues))

    async def validate_or_raise(
        self, payload: Any, context: ValidationContext, *, stop_on_first_error: bool = False
    ) -> None:
        """Run validation and raise when result is invalid."""
        result = await self.validate(payload, context, stop_on_first_error=stop_on_first_error)
        if not result.is_valid:
            raise ValidationFailedError(result)

