"""SQLAlchemy-backed repository adapter."""

from __future__ import annotations

import re
from dataclasses import asdict, is_dataclass
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Callable, Generic, Mapping, TypeVar
from uuid import uuid4

from sqlalchemy import Select, false as sa_false, func, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from eitohforge_sdk.application.dto.repository import (
    PaginationMode,
    QuerySpec,
    RepositoryContext,
    SortDirection,
    SortSpec,
)
from eitohforge_sdk.core.config import get_settings
from eitohforge_sdk.core.tenant import TenantContext
from eitohforge_sdk.domain.repositories.contracts import PageResult, RepositoryContract


TEntity = TypeVar("TEntity")
TCreate = TypeVar("TCreate")
TUpdate = TypeVar("TUpdate")


class SQLAlchemyRepository(
    Generic[TEntity, TCreate, TUpdate], RepositoryContract[TEntity, TCreate, TUpdate]
):
    """Contract-compliant SQLAlchemy repository implementation."""

    _SCHEMA_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        model_type: type[Any],
        to_entity: Callable[[Any], TEntity],
        create_to_values: Callable[[TCreate], dict[str, Any]] | None = None,
        update_to_values: Callable[[TUpdate], dict[str, Any]] | None = None,
        id_field: str = "id",
    ) -> None:
        self._session_factory = session_factory
        self._model_type = model_type
        self._to_entity = to_entity
        self._create_to_values = create_to_values or self._payload_to_values
        self._update_to_values = update_to_values or self._payload_to_values
        self._id_field = id_field
        self._columns = set(inspect(self._model_type).columns.keys())
        settings = get_settings()
        self._tenant_schema_isolation_enabled = settings.tenant.db_schema_isolation_enabled
        self._tenant_schema_name_template = settings.tenant.db_schema_name_template

    async def create(self, payload: TCreate, context: RepositoryContext | None = None) -> TEntity:
        values = self._create_to_values(payload)
        values = self._apply_write_context(values, context, is_create=True)
        if self._id_field in self._columns and self._id_field not in values:
            values[self._id_field] = str(uuid4())
        with self._session_factory() as session:
            self._apply_tenant_schema_isolation(session, context)
            model = self._model_type(**values)
            session.add(model)
            session.commit()
            session.refresh(model)
            return self._to_entity(model)

    async def get(self, entity_id: str, context: RepositoryContext | None = None) -> TEntity | None:
        with self._session_factory() as session:
            self._apply_tenant_schema_isolation(session, context)
            statement = self._base_statement(context).where(
                getattr(self._model_type, self._id_field) == entity_id
            )
            model = session.scalar(statement)
            if model is None:
                return None
            return self._to_entity(model)

    async def update(
        self, entity_id: str, payload: TUpdate, context: RepositoryContext | None = None
    ) -> TEntity | None:
        values = self._update_to_values(payload)
        values = self._apply_write_context(values, context, is_create=False)
        with self._session_factory() as session:
            self._apply_tenant_schema_isolation(session, context)
            statement = self._base_statement(context).where(
                getattr(self._model_type, self._id_field) == entity_id
            )
            model = session.scalar(statement)
            if model is None:
                return None
            for key, value in values.items():
                if key in self._columns:
                    setattr(model, key, value)
            session.commit()
            session.refresh(model)
            return self._to_entity(model)

    async def delete(self, entity_id: str, context: RepositoryContext | None = None) -> bool:
        with self._session_factory() as session:
            self._apply_tenant_schema_isolation(session, context)
            statement = self._base_statement(context).where(
                getattr(self._model_type, self._id_field) == entity_id
            )
            model = session.scalar(statement)
            if model is None:
                return False
            session.delete(model)
            session.commit()
            return True

    async def list(
        self, query: QuerySpec, context: RepositoryContext | None = None
    ) -> tuple[TEntity, ...]:
        with self._session_factory() as session:
            self._apply_tenant_schema_isolation(session, context)
            statement = self._apply_query(self._base_statement(context), query)
            statement = self._apply_pagination(statement, query)
            models = session.scalars(statement).all()
            return tuple(self._to_entity(model) for model in models)

    async def paginate(
        self, query: QuerySpec, context: RepositoryContext | None = None
    ) -> PageResult[TEntity]:
        with self._session_factory() as session:
            self._apply_tenant_schema_isolation(session, context)
            base_statement = self._base_statement(context)
            count_statement = select(func.count()).select_from(base_statement.subquery())
            total = int(session.scalar(count_statement) or 0)

            statement = self._apply_query(base_statement, query)
            statement = self._apply_pagination(statement, query)
            models = session.scalars(statement).all()
            items = tuple(self._to_entity(model) for model in models)
            next_cursor = self._resolve_next_cursor(models, query, total)
            return PageResult(
                items=items,
                total=total,
                page_size=query.pagination.page_size,
                next_cursor=next_cursor,
            )

    async def bulk_create(
        self, payloads: tuple[TCreate, ...], context: RepositoryContext | None = None
    ) -> tuple[TEntity, ...]:
        with self._session_factory() as session:
            self._apply_tenant_schema_isolation(session, context)
            models: list[Any] = []
            for payload in payloads:
                values = self._apply_write_context(self._create_to_values(payload), context, is_create=True)
                if self._id_field in self._columns and self._id_field not in values:
                    values[self._id_field] = str(uuid4())
                model = self._model_type(**values)
                models.append(model)
            session.add_all(models)
            session.commit()
            for model in models:
                session.refresh(model)
            return tuple(self._to_entity(model) for model in models)

    def _resolve_tenant_id_for_scope(self, context: RepositoryContext | None) -> str | None:
        if context is not None and context.tenant_id is not None:
            return context.tenant_id
        return TenantContext.current().tenant_id

    def _apply_tenant_schema_isolation(
        self,
        session: Session,
        context: RepositoryContext | None,
    ) -> None:
        """Optionally set Postgres `search_path` based on tenant id."""

        if not self._tenant_schema_isolation_enabled:
            return

        tenant_id = self._resolve_tenant_id_for_scope(context)
        if tenant_id is None:
            return

        bind = session.get_bind()
        dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
        if dialect_name not in {"postgresql"}:
            return

        template = self._tenant_schema_name_template
        schema_name = template.format(tenant_id=str(tenant_id).strip())
        if not self._SCHEMA_NAME_RE.match(schema_name):
            raise ValueError(f"Invalid tenant schema name resolved from tenant_id={tenant_id!r}.")

        # SET LOCAL affects the current transaction only.
        # Use SQLAlchemy `text()` so Session.execute is properly typed.
        session.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))

    def _base_statement(self, context: RepositoryContext | None) -> Select[Any]:
        statement = select(self._model_type)
        tenant_id = context.tenant_id if context is not None and context.tenant_id is not None else TenantContext.current().tenant_id
        if tenant_id is not None and "tenant_id" in self._columns:
            statement = statement.where(getattr(self._model_type, "tenant_id") == tenant_id)
        return statement

    def _apply_query(self, statement: Select[Any], query: QuerySpec) -> Select[Any]:
        """Apply ``QuerySpec`` filters and sorts. See ``docs/guides/query-spec-reference.md``."""
        for condition in query.filters:
            if condition.field not in self._columns:
                continue
            column = getattr(self._model_type, condition.field)
            operator = condition.operator.value
            if operator == "eq":
                statement = statement.where(column == condition.value)
            elif operator == "ne":
                statement = statement.where(column != condition.value)
            elif operator == "gt":
                statement = statement.where(column > condition.value)
            elif operator == "gte":
                statement = statement.where(column >= condition.value)
            elif operator == "lt":
                statement = statement.where(column < condition.value)
            elif operator == "lte":
                statement = statement.where(column <= condition.value)
            elif operator == "contains":
                statement = statement.where(column.contains(condition.value))
            elif operator == "startswith":
                statement = statement.where(column.startswith(condition.value))
            elif operator == "endswith":
                statement = statement.where(column.endswith(condition.value))
            elif operator == "between":
                bounds = self._extract_between_bounds(condition.value)
                if bounds is not None:
                    statement = statement.where(column.between(bounds[0], bounds[1]))
            elif operator == "in":
                values = self._extract_in_values(condition.value)
                if values is not None:
                    if len(values) == 0:
                        statement = statement.where(sa_false())
                    else:
                        statement = statement.where(column.in_(values))
            elif operator == "not_in":
                values = self._extract_in_values(condition.value)
                if values is not None:
                    if len(values) == 0:
                        pass
                    else:
                        statement = statement.where(column.not_in(values))
            elif operator == "exists":
                if bool(condition.value):
                    statement = statement.where(column.is_not(None))
                else:
                    statement = statement.where(column.is_(None))

        for sort in query.sorts:
            if sort.field not in self._columns:
                continue
            column = getattr(self._model_type, sort.field)
            statement = statement.order_by(column.asc() if sort.direction.value == "asc" else column.desc())
        return statement

    def _apply_write_context(
        self, values: dict[str, Any], context: RepositoryContext | None, *, is_create: bool
    ) -> dict[str, Any]:
        scoped = dict(values)
        tenant_id = context.tenant_id if context is not None and context.tenant_id is not None else TenantContext.current().tenant_id
        actor_id = context.actor_id if context is not None and context.actor_id is not None else TenantContext.current().actor_id
        if tenant_id is not None and "tenant_id" in self._columns and "tenant_id" not in scoped:
            scoped["tenant_id"] = tenant_id
        if actor_id is not None:
            if is_create and "created_by" in self._columns and "created_by" not in scoped:
                scoped["created_by"] = actor_id
            if "updated_by" in self._columns:
                scoped["updated_by"] = actor_id
        return scoped

    @staticmethod
    def _payload_to_values(payload: Any) -> dict[str, Any]:
        if isinstance(payload, Mapping):
            return dict(payload)
        if hasattr(payload, "model_dump"):
            return dict(payload.model_dump())
        if is_dataclass(payload) and not isinstance(payload, type):
            return dict(asdict(payload))
        if hasattr(payload, "__dict__"):
            return {key: value for key, value in vars(payload).items() if not key.startswith("_")}
        raise TypeError(f"Unsupported payload type: {type(payload)}")

    @staticmethod
    def _extract_between_bounds(value: Any) -> tuple[Any, Any] | None:
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 2:
            return (value[0], value[1])
        return None

    @staticmethod
    def _extract_in_values(value: Any) -> tuple[Any, ...] | None:
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return tuple(value)
        return None

    def _apply_pagination(self, statement: Select[Any], query: QuerySpec) -> Select[Any]:
        mode = query.pagination.mode
        if mode == PaginationMode.KEYSET:
            return self._apply_keyset_pagination(statement, query)

        offset = self._resolve_offset(query)
        return statement.offset(offset).limit(query.pagination.page_size)

    def _apply_keyset_pagination(self, statement: Select[Any], query: QuerySpec) -> Select[Any]:
        sort = self._get_primary_sort(query)
        if sort is None:
            return statement.limit(query.pagination.page_size)

        column = getattr(self._model_type, sort.field)
        cursor_value = query.pagination.cursor
        if cursor_value is not None:
            normalized = self._normalize_cursor_value(column, cursor_value)
            if sort.direction.value == "asc":
                statement = statement.where(column > normalized)
            else:
                statement = statement.where(column < normalized)
        return statement.limit(query.pagination.page_size)

    def _resolve_next_cursor(self, models: Sequence[Any], query: QuerySpec, total: int) -> str | None:
        if not models:
            return None
        mode = query.pagination.mode
        if mode == PaginationMode.KEYSET:
            sort = self._get_primary_sort(query)
            if sort is None:
                return None
            last_value = getattr(models[-1], sort.field, None)
            if last_value is None:
                return None
            return str(last_value)

        offset = self._resolve_offset(query)
        next_offset = offset + query.pagination.page_size
        return str(next_offset) if next_offset < total else None

    def _get_primary_sort(self, query: QuerySpec) -> SortSpec | None:
        if query.sorts:
            sort = query.sorts[0]
            if sort.field in self._columns:
                return sort
        if self._id_field in self._columns:
            return SortSpec(field=self._id_field, direction=SortDirection.ASC)
        return None

    @staticmethod
    def _resolve_offset(query: QuerySpec) -> int:
        cursor = query.pagination.cursor
        if query.pagination.mode == PaginationMode.CURSOR and cursor is not None and cursor.isdigit():
            return int(cursor)
        return query.pagination.offset

    @staticmethod
    def _normalize_cursor_value(column: Any, cursor: str) -> Any:
        try:
            python_type = column.type.python_type
        except Exception:
            return cursor

        if python_type is int:
            return int(cursor)
        if python_type is float:
            return float(cursor)
        if python_type is bool:
            return cursor.lower() in {"1", "true", "yes"}
        if python_type is datetime:
            return datetime.fromisoformat(cursor)
        return cursor

