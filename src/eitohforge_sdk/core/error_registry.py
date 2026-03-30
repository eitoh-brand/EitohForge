"""Error registry for mapping exceptions to API error contracts."""

from __future__ import annotations

from dataclasses import dataclass

from eitohforge_sdk.core.validation.errors import ValidationFailedError
from eitohforge_sdk.domain.value_objects.errors import DomainInvariantError


@dataclass(frozen=True)
class ErrorDefinition:
    """Mapping of exception type to standardized API error metadata."""

    code: str
    status_code: int
    default_message: str


class ErrorRegistry:
    """Registry resolving exception classes to error definitions."""

    def __init__(self) -> None:
        self._definitions: dict[type[BaseException], ErrorDefinition] = {}

    def register(self, exception_type: type[BaseException], definition: ErrorDefinition) -> None:
        self._definitions[exception_type] = definition

    def resolve(self, error: BaseException) -> ErrorDefinition:
        for candidate in type(error).mro():
            if candidate in self._definitions:
                return self._definitions[candidate]
        return ErrorDefinition(
            code="INTERNAL_SERVER_ERROR",
            status_code=500,
            default_message="An unexpected internal error occurred.",
        )


def build_default_error_registry() -> ErrorRegistry:
    """Build default exception mappings for SDK services."""
    registry = ErrorRegistry()
    registry.register(
        ValidationFailedError,
        ErrorDefinition(
            code="VALIDATION_FAILED",
            status_code=422,
            default_message="Request or business validation failed.",
        ),
    )
    registry.register(
        DomainInvariantError,
        ErrorDefinition(
            code="DOMAIN_INVARIANT_VIOLATION",
            status_code=422,
            default_message="Domain invariant validation failed.",
        ),
    )
    registry.register(
        PermissionError,
        ErrorDefinition(
            code="PERMISSION_DENIED",
            status_code=403,
            default_message="Permission denied.",
        ),
    )
    registry.register(
        KeyError,
        ErrorDefinition(
            code="RESOURCE_NOT_FOUND",
            status_code=404,
            default_message="Requested resource was not found.",
        ),
    )
    return registry

