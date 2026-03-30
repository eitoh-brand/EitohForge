from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, String, create_engine
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


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
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
    created_by: str | None
    updated_by: str | None


def _to_entity(model: UserModel) -> UserEntity:
    return UserEntity(
        entity_id=model.id,
        tenant_id=model.tenant_id,
        name=model.name,
        email=model.email,
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

