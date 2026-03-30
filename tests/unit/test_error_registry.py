from __future__ import annotations

from eitohforge_sdk.core.error_registry import ErrorDefinition, ErrorRegistry, build_default_error_registry
from eitohforge_sdk.core.validation.errors import ValidationFailedError, ValidationIssue, ValidationResult


class CustomValidationError(ValidationFailedError):
    pass


def test_error_registry_resolves_mro_specificity() -> None:
    registry = ErrorRegistry()
    registry.register(
        ValidationFailedError,
        ErrorDefinition(code="VALIDATION_FAILED", status_code=422, default_message="validation"),
    )
    definition = registry.resolve(
        CustomValidationError(ValidationResult(issues=(ValidationIssue(code="X", message="x"),)))
    )
    assert definition.code == "VALIDATION_FAILED"


def test_default_error_registry_contains_expected_mappings() -> None:
    registry = build_default_error_registry()
    definition = registry.resolve(KeyError("missing"))
    assert definition.status_code == 404
    assert definition.code == "RESOURCE_NOT_FOUND"

