from __future__ import annotations

import asyncio
from typing import Any

import fakeredis
import mongomock

from eitohforge_sdk.application.dto.repository import QuerySpec, RepositoryContext
from eitohforge_sdk.infrastructure.repositories.mongo_repository import MongoJsonRepository
from eitohforge_sdk.infrastructure.repositories.redis_repository import RedisJsonRepository


def _to_entity(row: dict[str, Any]) -> dict[str, Any]:
    return dict(row)


def test_redis_json_repository_crud_list() -> None:
    client = fakeredis.FakeRedis(decode_responses=True)
    repo = RedisJsonRepository[dict[str, Any], dict[str, Any], dict[str, Any]](
        redis_url="redis://localhost/0",
        key_prefix="unit:widgets",
        to_entity=_to_entity,
        client=client,
    )
    ctx = RepositoryContext(actor_id="a1", tenant_id="t1")

    async def _run() -> None:
        row = await repo.create({"id": "1", "name": "Ada", "score": 10}, ctx)
        assert row["tenant_id"] == "t1"
        g = await repo.get("1", ctx)
        assert g is not None
        listed = await repo.list(QuerySpec(), ctx)
        assert len(listed) == 1
        assert await repo.delete("1", ctx) is True
        assert await repo.get("1", ctx) is None

    asyncio.run(_run())


def test_mongo_json_repository_crud() -> None:
    col = mongomock.MongoClient()["db"]["coll"]
    repo = MongoJsonRepository[dict[str, Any], dict[str, Any], dict[str, Any]](
        collection=col,
        to_entity=_to_entity,
    )
    ctx = RepositoryContext(tenant_id="t1")

    async def _run() -> None:
        row = await repo.create({"id": "x1", "name": "Bob"}, ctx)
        assert row["id"] == "x1"
        g = await repo.get("x1", ctx)
        assert g is not None
        assert await repo.delete("x1", ctx) is True

    asyncio.run(_run())
