"""Reusable request/schema and cross-field validation rules."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from eitohforge_sdk.core.validation.context import ValidationContext
from eitohforge_sdk.core.validation.errors import ValidationIssue


TModel = TypeVar("TModel", bound=BaseModel)


@dataclass(frozen=True)
class PydanticSchemaRule(Generic[TModel]):
    """Validate payload shape with a Pydantic model."""

    model_type: type[TModel]
    name: str = "pydantic-schema-rule"

    async def validate(self, payload: Any, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        _ = context
        try:
            self.model_type.model_validate(payload)
            return ()
        except ValidationError as exc:
            issues: list[ValidationIssue] = []
            for error in exc.errors():
                loc = error.get("loc", ())
                field = ".".join(str(part) for part in loc) if loc else None
                issues.append(
                    ValidationIssue(
                        code=f"SCHEMA_{error.get('type', 'invalid').upper()}",
                        message=error.get("msg", "Invalid payload."),
                        field=field,
                    )
                )
            return tuple(issues)


@dataclass(frozen=True)
class RequiredTogetherRule:
    """Require both fields when either one is present."""

    left_field: str
    right_field: str
    name: str = "required-together-rule"

    async def validate(self, payload: Any, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        _ = context
        left_present, _ = _read_field(payload, self.left_field)
        right_present, _ = _read_field(payload, self.right_field)
        if left_present ^ right_present:
            return (
                ValidationIssue(
                    code="FIELDS_REQUIRED_TOGETHER",
                    message=f"Fields '{self.left_field}' and '{self.right_field}' must be provided together.",
                    field=self.left_field if left_present else self.right_field,
                ),
            )
        return ()


@dataclass(frozen=True)
class MutuallyExclusiveFieldsRule:
    """Ensure no more than one field is present."""

    fields: tuple[str, ...]
    name: str = "mutually-exclusive-fields-rule"

    async def validate(self, payload: Any, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        _ = context
        present_fields: list[str] = []
        for field in self.fields:
            present, _ = _read_field(payload, field)
            if present:
                present_fields.append(field)
        if len(present_fields) > 1:
            joined = ", ".join(present_fields)
            return (
                ValidationIssue(
                    code="FIELDS_MUTUALLY_EXCLUSIVE",
                    message=f"Fields are mutually exclusive: {joined}.",
                    field=present_fields[0],
                ),
            )
        return ()


@dataclass(frozen=True)
class FieldComparisonRule:
    """Compare two fields using a relational operator."""

    left_field: str
    right_field: str
    operator: str
    name: str = "field-comparison-rule"

    async def validate(self, payload: Any, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        _ = context
        left_present, left_value = _read_field(payload, self.left_field)
        right_present, right_value = _read_field(payload, self.right_field)
        if not left_present or not right_present:
            return ()

        operations = {
            "lt": lambda a, b: a < b,
            "lte": lambda a, b: a <= b,
            "gt": lambda a, b: a > b,
            "gte": lambda a, b: a >= b,
            "eq": lambda a, b: a == b,
            "ne": lambda a, b: a != b,
        }
        if self.operator not in operations:
            return (
                ValidationIssue(
                    code="FIELD_COMPARISON_INVALID_OPERATOR",
                    message=f"Unsupported comparison operator: {self.operator}",
                    field=self.left_field,
                ),
            )

        try:
            valid = operations[self.operator](left_value, right_value)
        except Exception:
            return (
                ValidationIssue(
                    code="FIELD_COMPARISON_TYPE_ERROR",
                    message=f"Fields '{self.left_field}' and '{self.right_field}' cannot be compared.",
                    field=self.left_field,
                ),
            )
        if valid:
            return ()
        return (
            ValidationIssue(
                code="FIELD_COMPARISON_FAILED",
                message=(
                    f"Field '{self.left_field}' must satisfy '{self.operator}' relation "
                    f"with '{self.right_field}'."
                ),
                field=self.left_field,
            ),
        )


def _read_field(payload: Any, field_name: str) -> tuple[bool, Any]:
    if isinstance(payload, BaseModel):
        data = payload.model_dump(exclude_unset=True)
        if field_name in data:
            return (True, data[field_name])
        return (False, None)
    if isinstance(payload, Mapping):
        if field_name in payload:
            return (True, payload[field_name])
        return (False, None)
    if hasattr(payload, field_name):
        value = getattr(payload, field_name)
        if value is None:
            return (False, None)
        return (True, value)
    return (False, None)

