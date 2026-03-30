from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sqlalchemy import DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from eitohforge_sdk.application.dto.repository import (
    FilterCondition,
    FilterOperator,
    PaginationMode,
    PaginationSpec,
    QuerySpec,
    RepositoryContext,
    SortDirection,
    SortSpec,
)
from eitohforge_sdk.infrastructure.repositories.sqlalchemy_repository import SQLAlchemyRepository
from eitohforge_sdk.core.tenant import TenantIsolationRule, register_tenant_context_middleware


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


@dataclass(frozen=True)
class UserEntity:
    entity_id: str
    tenant_id: str | None
    name: str
    email: str
    score: int
    created_by: str | None
    updated_by: str | None


def _to_entity(model: UserModel) -> UserEntity:
    return UserEntity(
        entity_id=model.id,
        tenant_id=model.tenant_id,
        name=model.name,
        email=model.email,
        score=model.score,
        created_by=model.created_by,
        updated_by=model.updated_by,
    )


def _build_repository(tmp_path: Path) -> SQLAlchemyRepository[UserEntity, dict[str, Any], dict[str, Any]]:
    db_file = tmp_path / "repo.sqlite3"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    return SQLAlchemyRepository(
        session_factory=factory,
        model_type=UserModel,
        to_entity=_to_entity,
    )


def test_sqlalchemy_repository_crud_bulk_list_paginate(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)
    tenant_a_ctx = RepositoryContext(actor_id="actor-a", tenant_id="tenant-a")
    tenant_b_ctx = RepositoryContext(actor_id="actor-b", tenant_id="tenant-b")

    created_a = asyncio.run(
        repository.create({"id": "u-a", "name": "Alice", "email": "alice@example.com"}, tenant_a_ctx)
    )
    created_b = asyncio.run(
        repository.create({"id": "u-b", "name": "Bob", "email": "bob@example.com"}, tenant_b_ctx)
    )
    assert created_a.created_by == "actor-a"
    assert created_b.created_by == "actor-b"

    fetched = asyncio.run(repository.get("u-a", tenant_a_ctx))
    assert fetched is not None
    assert fetched.name == "Alice"

    updated = asyncio.run(repository.update("u-a", {"name": "Alicia"}, tenant_a_ctx))
    assert updated is not None
    assert updated.name == "Alicia"
    assert updated.updated_by == "actor-a"

    asyncio.run(
        repository.bulk_create(
            (
                {"id": "u-c", "name": "Carl", "email": "carl@example.com"},
                {"id": "u-d", "name": "Dana", "email": "dana@example.com"},
            ),
            tenant_a_ctx,
        )
    )
    filtered = asyncio.run(
        repository.list(
            QuerySpec(filters=(FilterCondition(field="name", operator=FilterOperator.CONTAINS, value="a"),)),
            tenant_a_ctx,
        )
    )
    assert len(filtered) >= 2
    assert all(entity.tenant_id == "tenant-a" for entity in filtered)

    page = asyncio.run(
        repository.paginate(
            QuerySpec(pagination=PaginationSpec(page_size=2, offset=0)),
            tenant_a_ctx,
        )
    )
    assert page.total >= len(page.items)
    assert page.page_size == 2

    deleted = asyncio.run(repository.delete("u-a", tenant_a_ctx))
    assert deleted is True
    assert asyncio.run(repository.get("u-a", tenant_a_ctx)) is None


def test_sqlalchemy_repository_supports_between_in_not_in_and_sort(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)
    context = RepositoryContext(actor_id="actor-a", tenant_id="tenant-a")

    asyncio.run(
        repository.bulk_create(
            (
                {"id": "u-1", "name": "Abe", "email": "abe@example.com"},
                {"id": "u-2", "name": "Ben", "email": "ben@example.com"},
                {"id": "u-3", "name": "Cal", "email": "cal@example.com"},
            ),
            context,
        )
    )

    between_result = asyncio.run(
        repository.list(
            QuerySpec(
                filters=(
                    FilterCondition(
                        field="name",
                        operator=FilterOperator.BETWEEN,
                        value=["A", "Cz"],
                    ),
                ),
                sorts=(SortSpec(field="name", direction=SortDirection.ASC),),
            ),
            context,
        )
    )
    assert tuple(entity.name for entity in between_result) == ("Abe", "Ben", "Cal")

    in_result = asyncio.run(
        repository.list(
            QuerySpec(
                filters=(
                    FilterCondition(
                        field="name",
                        operator=FilterOperator.IN,
                        value=["Ben", "Cal"],
                    ),
                ),
                sorts=(SortSpec(field="name", direction=SortDirection.ASC),),
            ),
            context,
        )
    )
    assert tuple(entity.name for entity in in_result) == ("Ben", "Cal")

    not_in_result = asyncio.run(
        repository.list(
            QuerySpec(
                filters=(
                    FilterCondition(
                        field="name",
                        operator=FilterOperator.NOT_IN,
                        value=["Abe"],
                    ),
                ),
                sorts=(SortSpec(field="name", direction=SortDirection.DESC),),
            ),
            context,
        )
    )
    assert tuple(entity.name for entity in not_in_result) == ("Cal", "Ben")


def test_sqlalchemy_repository_cursor_pagination_offset_resolution(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)
    context = RepositoryContext(actor_id="actor-a", tenant_id="tenant-a")
    asyncio.run(
        repository.bulk_create(
            (
                {"id": "u-1", "name": "Abe", "email": "abe@example.com"},
                {"id": "u-2", "name": "Ben", "email": "ben@example.com"},
                {"id": "u-3", "name": "Cal", "email": "cal@example.com"},
            ),
            context,
        )
    )
    page = asyncio.run(
        repository.paginate(
            QuerySpec(
                pagination=PaginationSpec(page_size=1, offset=0, cursor="1", mode=PaginationMode.CURSOR),
                sorts=(SortSpec(field="name", direction=SortDirection.ASC),),
            ),
            context,
        )
    )
    assert len(page.items) == 1
    assert page.items[0].name == "Ben"


def test_sqlalchemy_repository_keyset_pagination_next_cursor(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)
    context = RepositoryContext(actor_id="actor-a", tenant_id="tenant-a")
    asyncio.run(
        repository.bulk_create(
            (
                {"id": "u-1", "name": "Abe", "email": "abe@example.com"},
                {"id": "u-2", "name": "Ben", "email": "ben@example.com"},
                {"id": "u-3", "name": "Cal", "email": "cal@example.com"},
            ),
            context,
        )
    )

    first_page = asyncio.run(
        repository.paginate(
            QuerySpec(
                pagination=PaginationSpec(page_size=2, mode=PaginationMode.KEYSET),
                sorts=(SortSpec(field="name", direction=SortDirection.ASC),),
            ),
            context,
        )
    )
    assert tuple(entity.name for entity in first_page.items) == ("Abe", "Ben")
    assert first_page.next_cursor == "Ben"

    second_page = asyncio.run(
        repository.paginate(
            QuerySpec(
                pagination=PaginationSpec(
                    page_size=2,
                    mode=PaginationMode.KEYSET,
                    cursor=first_page.next_cursor,
                ),
                sorts=(SortSpec(field="name", direction=SortDirection.ASC),),
            ),
            context,
        )
    )
    assert tuple(entity.name for entity in second_page.items) == ("Cal",)


def test_sqlalchemy_repository_blueprint_filter_operators(tmp_path: Path) -> None:
    """Cover §6-style operators: eq, ne, gt/gte/lt/lte, startswith/endswith, exists, empty in."""
    repository = _build_repository(tmp_path)
    context = RepositoryContext(actor_id="actor-a", tenant_id="tenant-a")

    asyncio.run(
        repository.bulk_create(
            (
                {
                    "id": "u-1",
                    "name": "Abe",
                    "email": "abe@example.com",
                    "score": 10,
                    "tenant_id": "tenant-a",
                    "created_by": "actor",
                },
                {
                    "id": "u-2",
                    "name": "Ben",
                    "email": "ben@corp.example.com",
                    "score": 20,
                    "tenant_id": "tenant-a",
                    "created_by": None,
                },
                {
                    "id": "u-3",
                    "name": "Cal",
                    "email": "cal@example.com",
                    "score": 15,
                    "tenant_id": "tenant-a",
                    "created_by": "actor",
                },
            ),
            None,
        )
    )

    eq_one = asyncio.run(
        repository.list(
            QuerySpec(filters=(FilterCondition(field="name", operator=FilterOperator.EQ, value="Ben"),)),
            context,
        ),
    )
    assert [e.name for e in eq_one] == ["Ben"]

    ne_q = asyncio.run(
        repository.list(
            QuerySpec(filters=(FilterCondition(field="name", operator=FilterOperator.NE, value="Abe"),)),
            context,
        )
    )
    assert set(e.name for e in ne_q) == {"Ben", "Cal"}

    gt_q = asyncio.run(
        repository.list(
            QuerySpec(
                filters=(FilterCondition(field="score", operator=FilterOperator.GT, value=12),),
                sorts=(SortSpec(field="score", direction=SortDirection.ASC),),
            ),
            context,
        )
    )
    assert [e.score for e in gt_q] == [15, 20]

    gte_q = asyncio.run(
        repository.list(
            QuerySpec(filters=(FilterCondition(field="score", operator=FilterOperator.GTE, value=20),)),
            context,
        )
    )
    assert [e.name for e in gte_q] == ["Ben"]

    lt_q = asyncio.run(
        repository.list(
            QuerySpec(filters=(FilterCondition(field="score", operator=FilterOperator.LT, value=16),)),
            context,
        )
    )
    assert set(e.name for e in lt_q) == {"Abe", "Cal"}

    lte_q = asyncio.run(
        repository.list(
            QuerySpec(filters=(FilterCondition(field="score", operator=FilterOperator.LTE, value=10),)),
            context,
        )
    )
    assert [e.name for e in lte_q] == ["Abe"]

    sw = asyncio.run(
        repository.list(
            QuerySpec(filters=(FilterCondition(field="email", operator=FilterOperator.STARTSWITH, value="ben@"),)),
            context,
        )
    )
    assert [e.name for e in sw] == ["Ben"]

    ew = asyncio.run(
        repository.list(
            QuerySpec(
                filters=(FilterCondition(field="email", operator=FilterOperator.ENDSWITH, value=".com"),),
                sorts=(SortSpec(field="name", direction=SortDirection.ASC),),
            ),
            context,
        )
    )
    assert [e.name for e in ew] == ["Abe", "Ben", "Cal"]

    exists_created_by = asyncio.run(
        repository.list(
            QuerySpec(filters=(FilterCondition(field="created_by", operator=FilterOperator.EXISTS, value=True),)),
            context,
        )
    )
    assert set(e.name for e in exists_created_by) == {"Abe", "Cal"}

    not_exists_created_by = asyncio.run(
        repository.list(
            QuerySpec(filters=(FilterCondition(field="created_by", operator=FilterOperator.EXISTS, value=False),)),
            context,
        )
    )
    assert [e.name for e in not_exists_created_by] == ["Ben"]

    empty_in = asyncio.run(
        repository.list(
            QuerySpec(filters=(FilterCondition(field="name", operator=FilterOperator.IN, value=[]),)),
            context,
        )
    )
    assert empty_in == ()


def test_sqlalchemy_repository_unknown_filter_field_is_skipped(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)
    context = RepositoryContext(actor_id="actor-a", tenant_id="tenant-a")
    asyncio.run(
        repository.create({"id": "u-1", "name": "Abe", "email": "abe@example.com"}, context)
    )
    rows = asyncio.run(
        repository.list(
            QuerySpec(
                filters=(FilterCondition(field="no_such_column", operator=FilterOperator.EQ, value="x"),),
            ),
            context,
        )
    )
    assert len(rows) == 1
    assert rows[0].name == "Abe"


def test_sqlalchemy_repository_auto_scopes_tenant_from_current_context(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)

    app = FastAPI()
    register_tenant_context_middleware(app, TenantIsolationRule())

    @app.post("/create")
    async def create() -> dict[str, str | None]:
        entity = await repository.create(
            {"id": "u-a", "name": "Alice", "email": "alice@example.com"},
            None,
        )
        return {"tenant_id": entity.tenant_id, "created_by": entity.created_by, "updated_by": entity.updated_by}

    @app.get("/list")
    async def list_for_tenant() -> dict[str, list[list[str | None]]]:
        items = await repository.list(QuerySpec(), None)
        return {"items": [[i.entity_id, i.tenant_id] for i in items]}

    client = TestClient(app)

    resp = client.post("/create", headers={"x-tenant-id": "tenant-a", "x-actor-id": "actor-a"})
    assert resp.status_code == 200
    assert resp.json()["tenant_id"] == "tenant-a"
    assert resp.json()["created_by"] == "actor-a"

    resp_a = client.get("/list", headers={"x-tenant-id": "tenant-a"})
    assert resp_a.status_code == 200
    assert resp_a.json()["items"] == [["u-a", "tenant-a"]]

    resp_b = client.get("/list", headers={"x-tenant-id": "tenant-b"})
    assert resp_b.status_code == 200
    assert resp_b.json()["items"] == []

