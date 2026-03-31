"""Redis-backed ``RepositoryContract`` (JSON documents per entity id)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Generic, TypeVar, cast
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


class RedisJsonRepository(Generic[TEntity, TCreate, TUpdate], RepositoryContract[TEntity, TCreate, TUpdate]):
    """Store each entity as a JSON string under ``{key_prefix}:row:{id}``; id set at ``{key_prefix}:ids``."""

    def __init__(
        self,
        *,
        redis_url: str,
        key_prefix: str = "eitohforge:repo:default",
        to_entity: Callable[[dict[str, Any]], TEntity],
        create_to_values: Callable[[TCreate], dict[str, Any]] | None = None,
        update_to_values: Callable[[TUpdate], dict[str, Any]] | None = None,
        id_field: str = "id",
        client: Any | None = None,
    ) -> None:
        if client is None:
            import redis as redis_module

            self._client = redis_module.Redis.from_url(redis_url, decode_responses=True)
        else:
            self._client = client
        self._key_prefix = key_prefix.strip().rstrip(":")
        self._ids_key = f"{self._key_prefix}:ids"
        self._to_entity = to_entity
        self._create_to_values = create_to_values or rh.payload_to_values
        self._update_to_values = update_to_values or rh.payload_to_values
        self._id_field = id_field

    def _row_key(self, entity_id: str) -> str:
        return f"{self._key_prefix}:row:{entity_id}"

    @staticmethod
    def _json_loads(raw: str | bytes) -> Any:
        if isinstance(raw, bytes):
            return json.loads(raw.decode("utf-8", errors="replace"))
        return json.loads(raw)

    def _load_all_rows(self) -> dict[str, dict[str, Any]]:
        ids_raw = self._client.smembers(self._ids_key)
        if isinstance(ids_raw, Awaitable):
            raise TypeError("RedisJsonRepository requires a synchronous redis client.")
        ids = cast(set[str], ids_raw)
        out: dict[str, dict[str, Any]] = {}
        for raw_id in ids or ():
            eid = str(raw_id)
            raw = self._client.get(self._row_key(eid))
            if raw is None:
                continue
            if isinstance(raw, Awaitable):
                raise TypeError("RedisJsonRepository requires a synchronous redis client.")
            raw_s = cast(str | bytes, raw)
            try:
                row = self._json_loads(raw_s)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                out[eid] = row
        return out

    def _create_sync(self, payload: TCreate, context: RepositoryContext | None) -> TEntity:
        values = dict(self._create_to_values(payload))
        values = rh.apply_write_context(values, context, is_create=True)
        if self._id_field not in values or values[self._id_field] is None:
            values[self._id_field] = str(uuid4())
        eid = str(values[self._id_field])
        self._client.sadd(self._ids_key, eid)
        self._client.set(self._row_key(eid), json.dumps(values, default=str))
        return self._to_entity(dict(values))

    def _get_sync(self, entity_id: str, context: RepositoryContext | None) -> TEntity | None:
        raw = self._client.get(self._row_key(entity_id))
        if raw is None:
            return None
        if isinstance(raw, Awaitable):
            raise TypeError("RedisJsonRepository requires a synchronous redis client.")
        try:
            row = self._json_loads(cast(str | bytes, raw))
        except json.JSONDecodeError:
            return None
        if not isinstance(row, dict) or not rh.row_in_tenant_scope(row, context):
            return None
        return self._to_entity(dict(row))

    def _update_sync(
        self, entity_id: str, payload: TUpdate, context: RepositoryContext | None
    ) -> TEntity | None:
        raw = self._client.get(self._row_key(entity_id))
        if raw is None:
            return None
        if isinstance(raw, Awaitable):
            raise TypeError("RedisJsonRepository requires a synchronous redis client.")
        try:
            row = self._json_loads(cast(str | bytes, raw))
        except json.JSONDecodeError:
            return None
        if not isinstance(row, dict) or not rh.row_in_tenant_scope(row, context):
            return None
        patch = self._update_to_values(payload)
        patch = rh.apply_write_context(dict(patch), context, is_create=False)
        merged = {**row, **patch}
        self._client.set(self._row_key(entity_id), json.dumps(merged, default=str))
        return self._to_entity(dict(merged))

    def _delete_sync(self, entity_id: str, context: RepositoryContext | None) -> bool:
        raw = self._client.get(self._row_key(entity_id))
        if raw is None:
            return False
        if isinstance(raw, Awaitable):
            raise TypeError("RedisJsonRepository requires a synchronous redis client.")
        try:
            row = self._json_loads(cast(str | bytes, raw))
        except json.JSONDecodeError:
            return False
        if not isinstance(row, dict) or not rh.row_in_tenant_scope(row, context):
            return False
        self._client.srem(self._ids_key, entity_id)
        self._client.delete(self._row_key(entity_id))
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
