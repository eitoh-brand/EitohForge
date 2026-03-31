"""Shared in-process filtering/sorting/pagination for dict-backed repositories."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, is_dataclass
from typing import Any, Mapping

from eitohforge_sdk.application.dto.repository import (
    FilterCondition,
    FilterOperator,
    PaginationMode,
    PaginationSpec,
    QuerySpec,
    RepositoryContext,
    SortDirection,
)
from eitohforge_sdk.core.tenant import TenantContext


def filtered_rows(
    rows: dict[str, dict[str, Any]],
    query: QuerySpec,
    context: RepositoryContext | None,
) -> list[dict[str, Any]]:
    """Return rows matching tenant scope, filters, and sorts (in-memory semantics)."""
    out = [dict(r) for r in rows.values() if row_in_tenant_scope(r, context)]
    for cond in query.filters:
        out = [r for r in out if matches_condition(r, cond)]
    for sort in query.sorts:
        reverse = sort.direction == SortDirection.DESC
        out.sort(key=lambda r: sort_key(r, sort.field), reverse=reverse)
    return out


def slice_page(rows: list[dict[str, Any]], pagination: PaginationSpec) -> list[dict[str, Any]]:
    offset = resolve_offset_from_spec(pagination)
    end = offset + pagination.page_size
    return rows[offset:end]


def resolve_offset_from_spec(pagination: PaginationSpec) -> int:
    if pagination.mode == PaginationMode.CURSOR and pagination.cursor is not None:
        if pagination.cursor.isdigit():
            return int(pagination.cursor)
    return pagination.offset


def row_in_tenant_scope(row: dict[str, Any], context: RepositoryContext | None) -> bool:
    tenant_id = (
        context.tenant_id
        if context is not None and context.tenant_id is not None
        else TenantContext.current().tenant_id
    )
    if tenant_id is None or "tenant_id" not in row:
        return True
    return row.get("tenant_id") == tenant_id


def apply_write_context(
    values: dict[str, Any], context: RepositoryContext | None, *, is_create: bool
) -> dict[str, Any]:
    scoped = dict(values)
    tenant_id = (
        context.tenant_id
        if context is not None and context.tenant_id is not None
        else TenantContext.current().tenant_id
    )
    actor_id = (
        context.actor_id
        if context is not None and context.actor_id is not None
        else TenantContext.current().actor_id
    )
    if tenant_id is not None and "tenant_id" not in scoped:
        scoped["tenant_id"] = tenant_id
    if actor_id is not None:
        if is_create and "created_by" not in scoped:
            scoped["created_by"] = actor_id
        scoped["updated_by"] = actor_id
    return scoped


def matches_condition(row: dict[str, Any], condition: FilterCondition) -> bool:
    if condition.field not in row:
        return False
    column = row[condition.field]
    op = condition.operator
    val = condition.value
    if op == FilterOperator.EQ:
        return bool(column == val)
    if op == FilterOperator.NE:
        return bool(column != val)
    if op == FilterOperator.GT:
        return bool(column > val)
    if op == FilterOperator.GTE:
        return bool(column >= val)
    if op == FilterOperator.LT:
        return bool(column < val)
    if op == FilterOperator.LTE:
        return bool(column <= val)
    if op == FilterOperator.CONTAINS:
        return val in str(column)
    if op == FilterOperator.STARTSWITH:
        return str(column).startswith(str(val))
    if op == FilterOperator.ENDSWITH:
        return str(column).endswith(str(val))
    if op == FilterOperator.BETWEEN:
        if isinstance(val, Sequence) and not isinstance(val, (str, bytes)) and len(val) == 2:
            return bool(val[0] <= column <= val[1])
        return False
    if op == FilterOperator.IN:
        if isinstance(val, Sequence) and not isinstance(val, (str, bytes)):
            return bool(column in tuple(val))
        return False
    if op == FilterOperator.NOT_IN:
        if isinstance(val, Sequence) and not isinstance(val, (str, bytes)):
            return bool(column not in tuple(val))
        return False
    if op == FilterOperator.EXISTS:
        if bool(val):
            return column is not None
        return column is None
    return False


def sort_key(row: dict[str, Any], field: str) -> Any:
    value = row.get(field)
    return (value is None, value)


def payload_to_values(payload: Any) -> dict[str, Any]:
    if isinstance(payload, Mapping):
        return dict(payload)
    if hasattr(payload, "model_dump"):
        return dict(payload.model_dump())
    if is_dataclass(payload) and not isinstance(payload, type):
        return dict(asdict(payload))
    if hasattr(payload, "__dict__"):
        return {k: v for k, v in vars(payload).items() if not k.startswith("_")}
    raise TypeError(f"Unsupported payload type: {type(payload)}")
