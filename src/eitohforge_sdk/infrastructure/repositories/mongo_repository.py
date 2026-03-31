"""MongoDB-backed ``RepositoryContract`` (optional ``pymongo`` extra)."""

from __future__ import annotations

import asyncio
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


def _require_pymongo() -> None:
    try:
        import pymongo  # noqa: F401
    except ImportError as exc:  # pragma: no cover - import guarded
        raise ImportError(
            "MongoJsonRepository requires pymongo. Install with: pip install 'eitohforge[mongo]'"
        ) from exc


class MongoJsonRepository(Generic[TEntity, TCreate, TUpdate], RepositoryContract[TEntity, TCreate, TUpdate]):
    """One document per entity; ``_id`` is the string entity id (same as ``id_field`` when set)."""

    def __init__(
        self,
        *,
        collection: Any,
        to_entity: Callable[[dict[str, Any]], TEntity],
        create_to_values: Callable[[TCreate], dict[str, Any]] | None = None,
        update_to_values: Callable[[TUpdate], dict[str, Any]] | None = None,
        id_field: str = "id",
    ) -> None:
        _require_pymongo()
        self._col = collection
        self._to_entity = to_entity
        self._create_to_values = create_to_values or rh.payload_to_values
        self._update_to_values = update_to_values or rh.payload_to_values
        self._id_field = id_field

    def _doc_to_row(self, doc: dict[str, Any]) -> dict[str, Any]:
        row = dict(doc)
        eid = row.pop("_id", None)
        if self._id_field not in row and eid is not None:
            row[self._id_field] = eid
        return row

    def _load_all_rows(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for doc in self._col.find():
            if not isinstance(doc, dict):
                continue
            row = self._doc_to_row(doc)
            eid = str(row.get(self._id_field) or doc.get("_id") or "")
            if eid:
                out[eid] = row
        return out

    def _create_sync(self, payload: TCreate, context: RepositoryContext | None) -> TEntity:
        values = dict(self._create_to_values(payload))
        values = rh.apply_write_context(values, context, is_create=True)
        if self._id_field not in values or values[self._id_field] is None:
            values[self._id_field] = str(uuid4())
        eid = str(values[self._id_field])
        doc = dict(values)
        doc["_id"] = eid
        self._col.replace_one({"_id": eid}, doc, upsert=True)
        return self._to_entity(dict(values))

    def _get_sync(self, entity_id: str, context: RepositoryContext | None) -> TEntity | None:
        doc = self._col.find_one({"_id": entity_id})
        if doc is None or not isinstance(doc, dict):
            return None
        row = self._doc_to_row(doc)
        if not rh.row_in_tenant_scope(row, context):
            return None
        return self._to_entity(dict(row))

    def _update_sync(
        self, entity_id: str, payload: TUpdate, context: RepositoryContext | None
    ) -> TEntity | None:
        doc = self._col.find_one({"_id": entity_id})
        if doc is None or not isinstance(doc, dict):
            return None
        row = self._doc_to_row(doc)
        if not rh.row_in_tenant_scope(row, context):
            return None
        patch = self._update_to_values(payload)
        patch = rh.apply_write_context(dict(patch), context, is_create=False)
        merged = {**row, **patch}
        merged[self._id_field] = entity_id
        out_doc = dict(merged)
        out_doc["_id"] = entity_id
        self._col.replace_one({"_id": entity_id}, out_doc, upsert=True)
        return self._to_entity(dict(merged))

    def _delete_sync(self, entity_id: str, context: RepositoryContext | None) -> bool:
        doc = self._col.find_one({"_id": entity_id})
        if doc is None or not isinstance(doc, dict):
            return False
        row = self._doc_to_row(doc)
        if not rh.row_in_tenant_scope(row, context):
            return False
        self._col.delete_one({"_id": entity_id})
        return True

    async def create(self, payload: TCreate, context: RepositoryContext | None = None) -> TEntity:
        return await asyncio.to_thread(self._create_sync, payload, context)

    async def get(self, entity_id: str, context: RepositoryContext | None = None) -> TEntity | None:
        return await asyncio.to_thread(self._get_sync, entity_id, context)

    async def update(
        self, entity_id: str, payload: TUpdate, context: RepositoryContext | None = None
    ) -> TEntity | None:
        return await asyncio.to_thread(self._update_sync, entity_id, payload, context)

    async def delete(self, entity_id: str, context: RepositoryContext | None = None) -> bool:
        return await asyncio.to_thread(self._delete_sync, entity_id, context)

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

        def _run() -> tuple[TEntity, ...]:
            rows = rh.filtered_rows(self._load_all_rows(), resolved, context)
            sliced = rh.slice_page(rows, resolved.pagination)
            return tuple(self._to_entity(dict(r)) for r in sliced)

        return await asyncio.to_thread(_run)

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

        def _run() -> PageResult[TEntity]:
            rows = rh.filtered_rows(self._load_all_rows(), resolved, context)
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

        return await asyncio.to_thread(_run)

    async def bulk_create(
        self, payloads: tuple[TCreate, ...], context: RepositoryContext | None = None
    ) -> tuple[TEntity, ...]:
        out: list[TEntity] = []
        for payload in payloads:
            out.append(await self.create(payload, context))
        return tuple(out)
