from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from eitohforge_sdk.application.dto.repository import RepositoryContext
from eitohforge_sdk.core.config import get_settings
from eitohforge_sdk.infrastructure.repositories.sqlalchemy_repository import SQLAlchemyRepository


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


class _FakeDialect:
    name: str = "postgresql"


class _FakeBind:
    dialect: _FakeDialect = _FakeDialect()


class _FakeSession:
    def __init__(self, *, executed: list[str]) -> None:
        self._executed = executed

    def __enter__(self) -> "_FakeSession":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:  # type: ignore[override]
        return None

    def get_bind(self) -> _FakeBind:
        return _FakeBind()

    def execute(self, stmt: Any) -> None:
        self._executed.append(str(stmt))

    def scalar(self, _statement: Any) -> Any:
        return None


class _FakeSessionFactory:
    def __init__(self, *, executed: list[str]) -> None:
        self._executed = executed

    def __call__(self) -> _FakeSession:
        return _FakeSession(executed=self._executed)


def test_tenant_schema_isolation_sets_search_path_for_postgresql(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EITOHFORGE_TENANT_DB_SCHEMA_ISOLATION_ENABLED", "true")
    monkeypatch.setenv("EITOHFORGE_TENANT_DB_SCHEMA_NAME_TEMPLATE", "{tenant_id}")
    get_settings.cache_clear()

    executed: list[str] = []
    session_factory: Any = _FakeSessionFactory(executed=executed)

    repo: SQLAlchemyRepository[Any, dict[str, Any], dict[str, Any]] = SQLAlchemyRepository(
        session_factory=session_factory,
        model_type=UserModel,
        to_entity=lambda _: {},
    )

    asyncio.run(repo.get("u-1", RepositoryContext(tenant_id="tenant-a")))

    assert any('SET LOCAL search_path' in sql for sql in executed)
    assert any('\"tenant-a\"' in sql for sql in executed)

