"""Typed DTO boundaries for repository operations."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FilterOperator(str, Enum):
    """Supported repository filter operations."""

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
    """Sort direction for repository queries."""

    ASC = "asc"
    DESC = "desc"


class PaginationMode(str, Enum):
    """Pagination strategy mode."""

    OFFSET = "offset"
    CURSOR = "cursor"
    KEYSET = "keyset"


class RepositoryContext(BaseModel):
    """Security, tenancy, and trace context for persistence calls."""

    model_config = ConfigDict(frozen=True)

    actor_id: str | None = None
    tenant_id: str | None = None
    request_id: str | None = None
    trace_id: str | None = None


class FilterCondition(BaseModel):
    """Filter predicate passed into repository list/paginate calls."""

    model_config = ConfigDict(frozen=True)

    field: str = Field(min_length=1)
    operator: FilterOperator = FilterOperator.EQ
    value: Any = None


class SortSpec(BaseModel):
    """Sort specification for repository queries."""

    model_config = ConfigDict(frozen=True)

    field: str = Field(min_length=1)
    direction: SortDirection = SortDirection.ASC


class PaginationSpec(BaseModel):
    """Pagination settings for repository queries."""

    model_config = ConfigDict(frozen=True)

    page_size: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
    cursor: str | None = None
    mode: PaginationMode = PaginationMode.OFFSET


class QuerySpec(BaseModel):
    """Container for filters, sorting, and pagination criteria."""

    model_config = ConfigDict(frozen=True)

    filters: tuple[FilterCondition, ...] = ()
    sorts: tuple[SortSpec, ...] = ()
    pagination: PaginationSpec = Field(default_factory=PaginationSpec)


class AuditMetadata(BaseModel):
    """Audit-safe metadata attached to persisted entities."""

    model_config = ConfigDict(frozen=True)

    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: str | None = None
    updated_by: str | None = None
    version: int = Field(default=1, ge=1)

