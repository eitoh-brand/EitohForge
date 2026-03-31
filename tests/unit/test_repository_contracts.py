from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

import pytest
from pydantic import ValidationError

from eitohforge_sdk.application.dto.repository import (
    Filter,
    FilterCondition,
    FilterOperator,
    Page,
    PaginationSpec,
    QuerySpec,
    RepositoryContext,
    Sort,
    SortSpec,
)
from eitohforge_sdk.domain.repositories.query_coalesce import coalesce_query_spec
from eitohforge_sdk.domain.repositories.specification import AndSpecification, Specification
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
        self,
        query: QuerySpec | None = None,
        context: RepositoryContext | None = None,
        *,
        filters: Sequence[FilterCondition | Specification] | None = None,
        sort: SortSpec | None = None,
        sorts: Sequence[SortSpec] | None = None,
        pagination: PaginationSpec | None = None,
    ) -> tuple[DummyEntity, ...]:
        _ = (query, context, filters, sort, sorts, pagination)
        return (DummyEntity(entity_id="1"),)

    async def paginate(
        self,
        query: QuerySpec | None = None,
        context: RepositoryContext | None = None,
        *,
        filters: Sequence[FilterCondition | Specification] | None = None,
        sort: SortSpec | None = None,
        sorts: Sequence[SortSpec] | None = None,
        pagination: PaginationSpec | None = None,
    ) -> PageResult[DummyEntity]:
        _ = (query, context, filters, sort, sorts, pagination)
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


def test_page_builder_uses_one_based_indexing() -> None:
    p = Page(2, page_size=10)
    assert p.offset == 10
    assert p.page_size == 10


def test_page_rejects_zero() -> None:
    with pytest.raises(ValueError):
        Page(0, page_size=10)


def test_coalesce_query_spec_rejects_mixed_sources() -> None:
    with pytest.raises(ValueError):
        coalesce_query_spec(QuerySpec(), filters=(Filter("a", "eq", 1),))


def test_and_specification_flattens_filters() -> None:
    @dataclass(frozen=True)
    class _NameEq:
        value: str

        def to_query_filters(self) -> tuple[FilterCondition, ...]:
            return (FilterCondition(field="name", operator=FilterOperator.EQ, value=self.value),)

    @dataclass(frozen=True)
    class _ScoreGte:
        value: int

        def to_query_filters(self) -> tuple[FilterCondition, ...]:
            return (FilterCondition(field="score", operator=FilterOperator.GTE, value=self.value),)

    spec = AndSpecification(parts=(_NameEq("x"), _ScoreGte(10)))
    filters = spec.to_query_filters()
    assert len(filters) == 2
    assert filters[0].field == "name"
    assert filters[1].field == "score"


def test_filter_sort_page_helpers_match_query_spec() -> None:
    q = coalesce_query_spec(
        None,
        filters=(Filter("age", "gt", 18),),
        sort=Sort("created_at", "desc"),
        pagination=Page(1, 20),
    )
    assert q.filters[0].operator.value == "gt"
    assert q.sorts[0].field == "created_at"
    assert q.sorts[0].direction.value == "desc"
    assert q.pagination.page_size == 20
    assert q.pagination.offset == 0

