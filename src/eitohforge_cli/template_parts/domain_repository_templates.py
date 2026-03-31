"""Domain repository template fragments (aligned with ``eitohforge_sdk.domain.repositories``)."""

DOMAIN_REPOSITORY_FILE_TEMPLATES: dict[str, str] = {
    "app/domain/repositories/__init__.py": """from app.domain.repositories.contracts import PageResult, RepositoryContract
from app.domain.repositories.query_coalesce import coalesce_query_spec, expand_filter_items
from app.domain.repositories.specification import AndSpecification, Specification

BaseRepository = RepositoryContract

__all__ = [
    "AndSpecification",
    "BaseRepository",
    "PageResult",
    "RepositoryContract",
    "Specification",
    "coalesce_query_spec",
    "expand_filter_items",
]
""",
    "app/domain/repositories/specification.py": """\"\"\"Composable query specifications that compile to repository filter tuples.\"\"\"

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.application.dto.repository import FilterCondition


@runtime_checkable
class Specification(Protocol):
    \"\"\"Maps to one or more ``FilterCondition`` rows (AND-composed by repositories).\"\"\"

    def to_query_filters(self) -> tuple[FilterCondition, ...]:
        \"\"\"Return filters merged with sibling criteria in document order.\"\"\"
        ...


@dataclass(frozen=True)
class AndSpecification:
    \"\"\"AND-composition of specifications (flattened to a single filter tuple).\"\"\"

    parts: tuple[Specification, ...]

    def to_query_filters(self) -> tuple[FilterCondition, ...]:
        return tuple(cond for part in self.parts for cond in part.to_query_filters())
""",
    "app/domain/repositories/query_coalesce.py": """\"\"\"Merge explicit ``QuerySpec`` with ergonomic filter/sort/pagination kwargs.\"\"\"

from __future__ import annotations

from collections.abc import Sequence

from app.application.dto.repository import FilterCondition, PaginationSpec, QuerySpec, SortSpec
from app.domain.repositories.specification import Specification


def expand_filter_items(items: Sequence[FilterCondition | Specification]) -> tuple[FilterCondition, ...]:
    \"\"\"Turn filters and specifications into a flat ``FilterCondition`` tuple.\"\"\"
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
    \"\"\"Return a single ``QuerySpec``; rejects mixing ``query=`` with keyword criteria.\"\"\"
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
""",
}
