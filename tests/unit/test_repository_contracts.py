from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import pytest
from pydantic import ValidationError

from eitohforge_sdk.application.dto.repository import PaginationSpec, QuerySpec, RepositoryContext
from eitohforge_sdk.domain.repositories.contracts import PageResult, RepositoryContract


@dataclass(frozen=True)
class DummyEntity:
    entity_id: str


@dataclass(frozen=True)
class DummyCreate:
    value: str


@dataclass(frozen=True)
class DummyUpdate:
    value: str


class DummyRepository:
    async def create(
        self, payload: DummyCreate, context: RepositoryContext | None = None
    ) -> DummyEntity:
        _ = context
        return DummyEntity(entity_id=payload.value)

    async def get(self, entity_id: str, context: RepositoryContext | None = None) -> DummyEntity | None:
        _ = context
        return DummyEntity(entity_id=entity_id)

    async def update(
        self, entity_id: str, payload: DummyUpdate, context: RepositoryContext | None = None
    ) -> DummyEntity | None:
        _ = (entity_id, context)
        return DummyEntity(entity_id=payload.value)

    async def delete(self, entity_id: str, context: RepositoryContext | None = None) -> bool:
        _ = (entity_id, context)
        return True

    async def list(
        self, query: QuerySpec, context: RepositoryContext | None = None
    ) -> tuple[DummyEntity, ...]:
        _ = (query, context)
        return (DummyEntity(entity_id="1"),)

    async def paginate(
        self, query: QuerySpec, context: RepositoryContext | None = None
    ) -> PageResult[DummyEntity]:
        _ = (query, context)
        return PageResult(items=(DummyEntity(entity_id="1"),), total=1, page_size=50)

    async def bulk_create(
        self, payloads: tuple[DummyCreate, ...], context: RepositoryContext | None = None
    ) -> tuple[DummyEntity, ...]:
        _ = context
        return tuple(DummyEntity(entity_id=payload.value) for payload in payloads)


def test_repository_contract_runtime_check() -> None:
    repository = DummyRepository()
    typed_repository = cast(RepositoryContract[DummyEntity, DummyCreate, DummyUpdate], repository)
    assert isinstance(typed_repository, RepositoryContract)


def test_pagination_spec_validates_bounds() -> None:
    with pytest.raises(ValidationError):
        PaginationSpec(page_size=0)


def test_query_spec_has_stable_defaults() -> None:
    query = QuerySpec()
    assert query.pagination.page_size == 50
    assert query.filters == ()

