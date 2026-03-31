"""Repository interfaces and page DTO for clean architecture boundaries."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar, runtime_checkable

from eitohforge_sdk.application.dto.repository import (
    FilterCondition,
    PaginationSpec,
    QuerySpec,
    RepositoryContext,
    SortSpec,
)
from eitohforge_sdk.domain.repositories.specification import Specification


TEntity = TypeVar("TEntity", covariant=True)
TCreate = TypeVar("TCreate", contravariant=True)
TUpdate = TypeVar("TUpdate", contravariant=True)


@dataclass(frozen=True)
class PageResult(Generic[TEntity]):
    """Paginated collection and associated metadata."""

    items: tuple[TEntity, ...]
    total: int
    page_size: int
    next_cursor: str | None = None


@runtime_checkable
class RepositoryContract(Protocol, Generic[TEntity, TCreate, TUpdate]):
    """Storage-agnostic repository operations contract."""

    async def create(self, payload: TCreate, context: RepositoryContext | None = None) -> TEntity:
        """Create and return a new entity."""

    async def get(self, entity_id: str, context: RepositoryContext | None = None) -> TEntity | None:
        """Fetch an entity by identifier."""

    async def update(
        self, entity_id: str, payload: TUpdate, context: RepositoryContext | None = None
    ) -> TEntity | None:
        """Update an entity and return it when present."""

    async def delete(self, entity_id: str, context: RepositoryContext | None = None) -> bool:
        """Delete an entity and return success status."""

    async def list(
        self,
        query: QuerySpec | None = None,
        context: RepositoryContext | None = None,
        *,
        filters: Sequence[FilterCondition | Specification] | None = None,
        sort: SortSpec | None = None,
        sorts: Sequence[SortSpec] | None = None,
        pagination: PaginationSpec | None = None,
    ) -> tuple[TEntity, ...]:
        """Return entities matching query criteria (``QuerySpec`` or ergonomic kwargs)."""

    async def paginate(
        self,
        query: QuerySpec | None = None,
        context: RepositoryContext | None = None,
        *,
        filters: Sequence[FilterCondition | Specification] | None = None,
        sort: SortSpec | None = None,
        sorts: Sequence[SortSpec] | None = None,
        pagination: PaginationSpec | None = None,
    ) -> PageResult[TEntity]:
        """Return paginated entity results (``QuerySpec`` or ergonomic kwargs)."""

    async def bulk_create(
        self, payloads: tuple[TCreate, ...], context: RepositoryContext | None = None
    ) -> tuple[TEntity, ...]:
        """Create multiple entities in one operation."""

