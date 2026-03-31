"""Typed DTO boundaries for repository operations."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FilterOperator(str, Enum):
    """Operators implemented by ``SQLAlchemyRepository`` (SQLAlchemy column semantics).

    Extensions: ``in`` / ``not_in`` (sequence values). ``exists`` maps to null checks: ``True`` →
    column IS NOT NULL, ``False`` → IS NULL (not SQL EXISTS subqueries).
    """

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
    """Filter predicate passed into repository list/paginate calls.

    ``between`` expects a sequence of exactly two bounds. ``in`` / ``not_in`` expect a non-string
    sequence (empty ``in`` matches no rows; empty ``not_in`` is a no-op). Unknown ``field`` names
    are ignored by the repository (no error) unless you pre-validate with
    ``validate_query_filters_against_columns``.
    """

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


QueryFilter = FilterCondition
"""Alias for documentation and NestJS-style naming (same as ``FilterCondition``)."""


def Filter(field: str, operator: str | FilterOperator, value: Any) -> FilterCondition:
    """Build a filter using string operators (e.g. ``\"gt\"``) or ``FilterOperator``."""
    op = operator if isinstance(operator, FilterOperator) else FilterOperator(operator)
    return FilterCondition(field=field, operator=op, value=value)


def Sort(field: str, direction: str | SortDirection = SortDirection.ASC) -> SortSpec:
    """Build a sort spec using string direction (``\"asc\"`` / ``\"desc\"``) or ``SortDirection``."""
    dir_ = direction if isinstance(direction, SortDirection) else SortDirection(direction)
    return SortSpec(field=field, direction=dir_)


def Page(page: int, page_size: int = 50, *, mode: PaginationMode = PaginationMode.OFFSET) -> PaginationSpec:
    """1-based page index into ``PaginationSpec`` (offset is ``(page - 1) * page_size``)."""
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
    """Construct a ``QuerySpec`` without mixing ``sort`` and ``sorts``."""
    if sort is not None and sorts is not None:
        raise ValueError("Pass either sort= or sorts=, not both.")
    s = (sort,) if sort is not None else tuple(sorts or ())
    p = pagination if pagination is not None else PaginationSpec()
    return QuerySpec(filters=tuple(filters), sorts=s, pagination=p)


class AuditMetadata(BaseModel):
    """Audit-safe metadata attached to persisted entities."""

    model_config = ConfigDict(frozen=True)

    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: str | None = None
    updated_by: str | None = None
    version: int = Field(default=1, ge=1)

