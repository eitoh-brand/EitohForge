"""Application-layer scaffold template fragments."""

APPLICATION_FILE_TEMPLATES: dict[str, str] = {
    "app/application/__init__.py": """from app.application.services.validation import ServiceValidationHooks
""",
    "app/application/dto/__init__.py": """from app.application.dto.error import ApiError, ApiErrorDetail, ApiErrorResponse
from app.application.dto.repository import (
    AuditMetadata,
    Filter,
    FilterCondition,
    FilterOperator,
    Page,
    PaginationMode,
    PaginationSpec,
    QueryFilter,
    QuerySpec,
    RepositoryContext,
    Sort,
    SortDirection,
    SortSpec,
    list_query,
)
from app.application.dto.response import (
    ApiResponse,
    ApiResponseMeta,
    PaginatedApiResponse,
    PaginationMeta,
)
""",
    "app/application/dto/repository.py": """from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FilterOperator(str, Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    CONTAINS = "contains"
    STARTSWITH = "startswith"
    ENDSWITH = "endswith"
    BETWEEN = "between"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


class PaginationMode(str, Enum):
    OFFSET = "offset"
    CURSOR = "cursor"
    KEYSET = "keyset"


class RepositoryContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    actor_id: str | None = None
    tenant_id: str | None = None
    request_id: str | None = None
    trace_id: str | None = None


class FilterCondition(BaseModel):
    model_config = ConfigDict(frozen=True)

    field: str = Field(min_length=1)
    operator: FilterOperator = FilterOperator.EQ
    value: Any = None


class SortSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    field: str = Field(min_length=1)
    direction: SortDirection = SortDirection.ASC


class PaginationSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    page_size: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
    cursor: str | None = None
    mode: PaginationMode = PaginationMode.OFFSET


class QuerySpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    filters: tuple[FilterCondition, ...] = ()
    sorts: tuple[SortSpec, ...] = ()
    pagination: PaginationSpec = Field(default_factory=PaginationSpec)


QueryFilter = FilterCondition


def Filter(field: str, operator: str | FilterOperator, value: Any) -> FilterCondition:
    op = operator if isinstance(operator, FilterOperator) else FilterOperator(operator)
    return FilterCondition(field=field, operator=op, value=value)


def Sort(field: str, direction: str | SortDirection = SortDirection.ASC) -> SortSpec:
    dir_ = direction if isinstance(direction, SortDirection) else SortDirection(direction)
    return SortSpec(field=field, direction=dir_)


def Page(page: int, page_size: int = 50, *, mode: PaginationMode = PaginationMode.OFFSET) -> PaginationSpec:
    if page < 1:
        raise ValueError("Page must be >= 1 (1-based).")
    return PaginationSpec(
        page_size=page_size,
        offset=(page - 1) * page_size,
        mode=mode,
    )


def list_query(
    *,
    filters: Sequence[FilterCondition] = (),
    sort: SortSpec | None = None,
    sorts: Sequence[SortSpec] | None = None,
    pagination: PaginationSpec | None = None,
) -> QuerySpec:
    if sort is not None and sorts is not None:
        raise ValueError("Pass either sort= or sorts=, not both.")
    s = (sort,) if sort is not None else tuple(sorts or ())
    p = pagination if pagination is not None else PaginationSpec()
    return QuerySpec(filters=tuple(filters), sorts=s, pagination=p)


class AuditMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: str | None = None
    updated_by: str | None = None
    version: int = Field(default=1, ge=1)
""",
    "app/application/dto/error.py": """from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.dto.response import ApiResponseMeta


class ApiErrorDetail(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    field: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class ApiError(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    details: tuple[ApiErrorDetail, ...] = ()


class ApiErrorResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: Literal[False] = False
    error: ApiError
    meta: ApiResponseMeta = Field(default_factory=ApiResponseMeta)
""",
    "app/application/dto/response.py": """from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiResponseMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str | None = None
    trace_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PaginationMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    total: int = Field(ge=0)
    page_size: int = Field(ge=1)
    next_cursor: str | None = None


class ApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool = True
    data: object | None = None
    message: str | None = None
    meta: ApiResponseMeta = Field(default_factory=ApiResponseMeta)


class PaginatedApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool = True
    data: tuple[object, ...] = ()
    pagination: PaginationMeta
    message: str | None = None
    meta: ApiResponseMeta = Field(default_factory=ApiResponseMeta)
""",
    "app/application/use_cases/__init__.py": "",
    "app/application/requests/__init__.py": "",
    "app/application/responses/__init__.py": "",
    "app/application/services/__init__.py": """from app.application.services.validation import ServiceValidationHooks
""",
    "app/application/services/validation.py": """from dataclasses import replace
from typing import Any

from app.core.validation.context import ValidationContext, ValidationStage
from app.core.validation.engine import ValidationEngine
from app.core.validation.hooks import BusinessValidationHook, SecurityValidationHook


class ServiceValidationHooks:
    def __init__(
        self,
        *,
        business_hooks: tuple[BusinessValidationHook, ...] = (),
        security_hooks: tuple[SecurityValidationHook, ...] = (),
    ) -> None:
        self._business_engine = ValidationEngine()
        self._security_engine = ValidationEngine()
        self.register_business_hooks(business_hooks)
        self.register_security_hooks(security_hooks)

    def register_business_hook(self, hook: BusinessValidationHook) -> None:
        self._business_engine.register(hook)

    def register_business_hooks(self, hooks: tuple[BusinessValidationHook, ...]) -> None:
        self._business_engine.register_many(hooks)

    def register_security_hook(self, hook: SecurityValidationHook) -> None:
        self._security_engine.register(hook)

    def register_security_hooks(self, hooks: tuple[SecurityValidationHook, ...]) -> None:
        self._security_engine.register_many(hooks)

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
""",
}

