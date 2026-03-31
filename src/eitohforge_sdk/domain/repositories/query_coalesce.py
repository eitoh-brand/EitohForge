"""Merge explicit ``QuerySpec`` with ergonomic filter/sort/pagination kwargs."""

from __future__ import annotations

from collections.abc import Sequence

from eitohforge_sdk.application.dto.repository import (
    FilterCondition,
    PaginationSpec,
    QuerySpec,
    SortSpec,
)
from eitohforge_sdk.domain.repositories.specification import Specification


def expand_filter_items(items: Sequence[FilterCondition | Specification]) -> tuple[FilterCondition, ...]:
    """Turn filters and specifications into a flat ``FilterCondition`` tuple."""
    out: list[FilterCondition] = []
    for item in items:
        if isinstance(item, FilterCondition):
            out.append(item)
        elif isinstance(item, Specification):
            out.extend(item.to_query_filters())
        else:
            raise TypeError(f"Unsupported filter/specification entry: {type(item)!r}.")
    return tuple(out)


def _merge_sorts(
    sort: SortSpec | None, sorts: Sequence[SortSpec] | None
) -> tuple[SortSpec, ...]:
    if sort is not None and sorts is not None:
        raise ValueError("Pass either sort= or sorts=, not both.")
    if sort is not None:
        return (sort,)
    if sorts is not None:
        return tuple(sorts)
    return ()


def coalesce_query_spec(
    query: QuerySpec | None,
    *,
    filters: Sequence[FilterCondition | Specification] | None = None,
    sort: SortSpec | None = None,
    sorts: Sequence[SortSpec] | None = None,
    pagination: PaginationSpec | None = None,
) -> QuerySpec:
    """Return a single ``QuerySpec``; rejects mixing ``query=`` with keyword criteria."""
    has_kw = (
        filters is not None
        or sort is not None
        or sorts is not None
        or pagination is not None
    )
    if query is not None and has_kw:
        raise ValueError("Pass either query= or filter/sort/pagination kwargs, not both.")
    if query is not None:
        return query
    f = expand_filter_items(filters or ())
    s = _merge_sorts(sort, sorts)
    p = pagination if pagination is not None else PaginationSpec()
    return QuerySpec(filters=f, sorts=s, pagination=p)
