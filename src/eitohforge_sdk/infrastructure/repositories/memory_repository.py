"""In-memory ``RepositoryContract`` implementation for tests and non-SQL backends."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Generic, TypeVar
from uuid import uuid4

from eitohforge_sdk.application.dto.repository import (
    FilterCondition,
    PaginationSpec,
    QuerySpec,
    RepositoryContext,
    SortSpec,
)
from eitohforge_sdk.domain.repositories.contracts import PageResult, RepositoryContract
from eitohforge_sdk.domain.repositories.query_coalesce import coalesce_query_spec
from eitohforge_sdk.domain.repositories.specification import Specification
from eitohforge_sdk.infrastructure.repositories import repository_row_helpers as rh


TEntity = TypeVar("TEntity")
TCreate = TypeVar("TCreate")
TUpdate = TypeVar("TUpdate")


class InMemoryRepository(Generic[TEntity, TCreate, TUpdate], RepositoryContract[TEntity, TCreate, TUpdate]):
    """Dict-backed repository; applies ``QuerySpec`` filters in-process."""

    def __init__(
        self,
        *,
        to_entity: Callable[[dict[str, Any]], TEntity],
        create_to_values: Callable[[TCreate], dict[str, Any]] | None = None,
        update_to_values: Callable[[TUpdate], dict[str, Any]] | None = None,
        id_field: str = "id",
    ) -> None:
        self._to_entity = to_entity
        self._create_to_values = create_to_values or rh.payload_to_values
        self._update_to_values = update_to_values or rh.payload_to_values
        self._id_field = id_field
        self._rows: dict[str, dict[str, Any]] = {}

    async def create(self, payload: TCreate, context: RepositoryContext | None = None) -> TEntity:
        values = dict(self._create_to_values(payload))
        values = rh.apply_write_context(values, context, is_create=True)
        if self._id_field not in values or values[self._id_field] is None:
            values[self._id_field] = str(uuid4())
        eid = str(values[self._id_field])
        self._rows[eid] = values
        return self._to_entity(dict(values))

    async def get(self, entity_id: str, context: RepositoryContext | None = None) -> TEntity | None:
        row = self._rows.get(entity_id)
        if row is None or not rh.row_in_tenant_scope(row, context):
            return None
        return self._to_entity(dict(row))

    async def update(
        self, entity_id: str, payload: TUpdate, context: RepositoryContext | None = None
    ) -> TEntity | None:
        row = self._rows.get(entity_id)
        if row is None or not rh.row_in_tenant_scope(row, context):
            return None
        patch = self._update_to_values(payload)
        patch = rh.apply_write_context(dict(patch), context, is_create=False)
        merged = {**row, **patch}
        self._rows[entity_id] = merged
        return self._to_entity(dict(merged))

    async def delete(self, entity_id: str, context: RepositoryContext | None = None) -> bool:
        row = self._rows.get(entity_id)
        if row is None or not rh.row_in_tenant_scope(row, context):
            return False
        del self._rows[entity_id]
        return True

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
        resolved = coalesce_query_spec(
            query,
            filters=filters,
            sort=sort,
            sorts=sorts,
            pagination=pagination,
        )
        rows = rh.filtered_rows(self._rows, resolved, context)
        sliced = rh.slice_page(rows, resolved.pagination)
        return tuple(self._to_entity(dict(r)) for r in sliced)

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
        resolved = coalesce_query_spec(
            query,
            filters=filters,
            sort=sort,
            sorts=sorts,
            pagination=pagination,
        )
        rows = rh.filtered_rows(self._rows, resolved, context)
        total = len(rows)
        sliced = rh.slice_page(rows, resolved.pagination)
        items = tuple(self._to_entity(dict(r)) for r in sliced)
        offset = rh.resolve_offset_from_spec(resolved.pagination)
        next_offset = offset + resolved.pagination.page_size
        next_cursor = str(next_offset) if next_offset < total else None
        return PageResult(
            items=items,
            total=total,
            page_size=resolved.pagination.page_size,
            next_cursor=next_cursor,
        )

    async def bulk_create(
        self, payloads: tuple[TCreate, ...], context: RepositoryContext | None = None
    ) -> tuple[TEntity, ...]:
        out: list[TEntity] = []
        for payload in payloads:
            out.append(await self.create(payload, context))
        return tuple(out)
