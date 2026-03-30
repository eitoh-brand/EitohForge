"""Validation core template fragments."""

CORE_VALIDATION_FILE_TEMPLATES: dict[str, str] = {
    'app/core/validation/__init__.py': """from app.core.validation.context import ValidationContext, ValidationStage
from app.core.validation.contracts import ValidationRule
from app.core.validation.engine import ValidationEngine
from app.core.validation.errors import (
    ValidationFailedError,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)
from app.core.validation.hooks import (
    AuthenticatedActorSecurityHook,
    BusinessValidationHook,
    PermissionSecurityHook,
    SecurityValidationHook,
    TenantScopeBusinessHook,
)
from app.core.validation.rules import (
    FieldComparisonRule,
    MutuallyExclusiveFieldsRule,
    PydanticSchemaRule,
    RequiredTogetherRule,
)
""",
    'app/core/validation/context.py': """from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ValidationStage(str, Enum):
    REQUEST = "request"
    DOMAIN = "domain"
    BUSINESS = "business"
    SECURITY = "security"


@dataclass(frozen=True)
class ValidationContext:
    stage: ValidationStage
    actor_id: str | None = None
    tenant_id: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
""",
    'app/core/validation/contracts.py': """from typing import Generic, Protocol, TypeVar

from app.core.validation.context import ValidationContext
from app.core.validation.errors import ValidationIssue


TPayload = TypeVar("TPayload", contravariant=True)


class ValidationRule(Protocol, Generic[TPayload]):
    name: str

    async def validate(
        self, payload: TPayload, context: ValidationContext
    ) -> tuple[ValidationIssue, ...]:
        ...
""",
    'app/core/validation/errors.py': """from dataclasses import dataclass
from enum import Enum


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    field: str | None = None
    severity: ValidationSeverity = ValidationSeverity.ERROR


@dataclass(frozen=True)
class ValidationResult:
    issues: tuple[ValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)


class ValidationFailedError(ValueError):
    def __init__(self, result: ValidationResult):
        self.result = result
        summary = "; ".join(f"{issue.code}: {issue.message}" for issue in result.issues)
        super().__init__(summary or "Validation failed.")
""",
    'app/core/validation/engine.py': """from collections.abc import Iterable
from typing import Any

from app.core.validation.context import ValidationContext
from app.core.validation.contracts import ValidationRule
from app.core.validation.errors import ValidationFailedError, ValidationIssue, ValidationResult


class ValidationEngine:
    def __init__(self) -> None:
        self._rules: list[ValidationRule[Any]] = []

    def register(self, rule: ValidationRule[Any]) -> None:
        self._rules.append(rule)

    def register_many(self, rules: Iterable[ValidationRule[Any]]) -> None:
        for rule in rules:
            self.register(rule)

    async def validate(
        self,
        payload: Any,
        context: ValidationContext,
        *,
        stop_on_first_error: bool = False,
    ) -> ValidationResult:
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
        result = await self.validate(payload, context, stop_on_first_error=stop_on_first_error)
        if not result.is_valid:
            raise ValidationFailedError(result)
""",
    'app/core/validation/hooks.py': """from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel

from app.core.validation.context import ValidationContext
from app.core.validation.errors import ValidationIssue


class BusinessValidationHook(Protocol):
    name: str

    async def validate(self, payload: Any, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        ...


class SecurityValidationHook(Protocol):
    name: str

    async def validate(self, payload: Any, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        ...


@dataclass(frozen=True)
class TenantScopeBusinessHook:
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
        return {str(item) for item in raw_permissions}
    return set()


def _read_field(payload: Any, field_name: str) -> Any | None:
    if isinstance(payload, BaseModel):
        return payload.model_dump(exclude_unset=True).get(field_name)
    if isinstance(payload, Mapping):
        return payload.get(field_name)
    if hasattr(payload, field_name):
        return getattr(payload, field_name)
    return None
""",
    'app/core/validation/rules.py': """from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.validation.context import ValidationContext
from app.core.validation.errors import ValidationIssue


@dataclass(frozen=True)
class PydanticSchemaRule:
    model_type: type[BaseModel]
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
""",
}
