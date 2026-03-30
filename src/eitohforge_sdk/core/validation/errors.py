"""Validation issue and result models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ValidationSeverity(str, Enum):
    """Severity levels for validation findings."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class ValidationIssue:
    """Single validation issue."""

    code: str
    message: str
    field: str | None = None
    severity: ValidationSeverity = ValidationSeverity.ERROR


@dataclass(frozen=True)
class ValidationResult:
    """Aggregate result from validation engine execution."""

    issues: tuple[ValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        """Return True when there are no error-severity issues."""
        return not any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)


class ValidationFailedError(ValueError):
    """Raised when validation fails with one or more issues."""

    def __init__(self, result: ValidationResult):
        self.result = result
        summary = "; ".join(f"{issue.code}: {issue.message}" for issue in result.issues)
        super().__init__(summary or "Validation failed.")

