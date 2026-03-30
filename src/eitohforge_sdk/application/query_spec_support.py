"""Helpers to validate ``QuerySpec`` against known model columns before repository calls."""

from __future__ import annotations

from eitohforge_sdk.application.dto.repository import QuerySpec


def list_unknown_query_filter_fields(
    query: QuerySpec, *, valid_columns: set[str]
) -> tuple[str, ...]:
    """Return filter field names that are not in ``valid_columns`` (may contain duplicates)."""
    return tuple(f.field for f in query.filters if f.field not in valid_columns)


def validate_query_filters_against_columns(query: QuerySpec, *, valid_columns: set[str]) -> None:
    """Raise ``ValueError`` if any filter references a column name absent from ``valid_columns``."""
    unknown = sorted(set(list_unknown_query_filter_fields(query, valid_columns=valid_columns)))
    if unknown:
        raise ValueError(f"Query references unknown filter field(s): {unknown}")
