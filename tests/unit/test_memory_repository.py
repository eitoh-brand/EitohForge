from __future__ import annotations

import asyncio
from typing import Any

from eitohforge_sdk.application.dto.repository import (
    Filter,
    FilterCondition,
    FilterOperator,
    Page,
    QuerySpec,
    RepositoryContext,
    Sort,
)
from eitohforge_sdk.infrastructure.repositories.memory_repository import InMemoryRepository


def _to_entity(row: dict[str, Any]) -> dict[str, Any]:
    return dict(row)


def test_in_memory_repository_crud_list_paginate() -> None:
    repo = InMemoryRepository[dict[str, Any], dict[str, Any], dict[str, Any]](to_entity=_to_entity)
    ctx = RepositoryContext(actor_id="a1", tenant_id="t1")

    async def _run() -> None:
        u1 = await repo.create({"id": "1", "name": "Ada", "score": 10}, ctx)
        assert u1["name"] == "Ada"
        assert u1["tenant_id"] == "t1"
        g = await repo.get("1", ctx)
        assert g is not None
        assert g["name"] == "Ada"
        await repo.update("1", {"name": "Ada2"}, ctx)
        listed = await repo.list(
            filters=(Filter("score", "gte", 5),),
            sort=Sort("name", "asc"),
            pagination=Page(1, 10),
            context=ctx,
        )
        assert len(listed) == 1
        assert listed[0]["name"] == "Ada2"
        page = await repo.paginate(QuerySpec(), ctx)
        assert page.total >= 1
        assert await repo.delete("1", ctx) is True
        assert await repo.get("1", ctx) is None

    asyncio.run(_run())


def test_in_memory_repository_delete_get_miss() -> None:
    repo = InMemoryRepository[dict[str, Any], dict[str, Any], dict[str, Any]](to_entity=_to_entity)

    async def _run() -> None:
        assert await repo.delete("missing", None) is False
        assert await repo.get("missing", None) is None

    asyncio.run(_run())


def test_in_memory_repository_bulk_create() -> None:
    repo = InMemoryRepository[dict[str, Any], dict[str, Any], dict[str, Any]](to_entity=_to_entity)

    async def _run() -> None:
        rows = await repo.bulk_create(({"id": "a", "n": 1}, {"id": "b", "n": 2}), None)
        assert len(rows) == 2
        assert await repo.get("b", None) is not None

    asyncio.run(_run())


def test_in_memory_repository_more_filter_operators() -> None:
    repo = InMemoryRepository[dict[str, Any], dict[str, Any], dict[str, Any]](to_entity=_to_entity)

    async def _run() -> None:
        await repo.create({"id": "1", "label": "hello", "n": 5}, None)
        await repo.create({"id": "2", "label": "world", "n": 15}, None)
        q1 = await repo.list(
            QuerySpec(filters=(FilterCondition(field="label", operator=FilterOperator.STARTSWITH, value="he"),)),
            None,
        )
        assert len(q1) == 1
        q2 = await repo.list(
            QuerySpec(filters=(FilterCondition(field="n", operator=FilterOperator.BETWEEN, value=(10, 20)),)),
            None,
        )
        assert len(q2) == 1
        q3 = await repo.list(
            QuerySpec(filters=(FilterCondition(field="label", operator=FilterOperator.NOT_IN, value=("world",)),)),
            None,
        )
        assert len(q3) == 1

    asyncio.run(_run())


def test_in_memory_repository_filter_in_empty_matches_none() -> None:
    repo = InMemoryRepository[dict[str, Any], dict[str, Any], dict[str, Any]](to_entity=_to_entity)

    async def _run() -> None:
        await repo.create({"id": "1", "name": "x"}, None)
        from eitohforge_sdk.application.dto.repository import FilterCondition

        rows = await repo.list(
            QuerySpec(
                filters=(
                    FilterCondition(field="name", operator=FilterOperator.IN, value=()),
                )
            ),
            None,
        )
        assert len(rows) == 0

    asyncio.run(_run())
