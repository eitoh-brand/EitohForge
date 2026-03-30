import pytest

from eitohforge_sdk.core.config import AppSettings
from eitohforge_sdk.infrastructure.database.factory import build_database_provider, build_database_registry
from eitohforge_sdk.infrastructure.database.providers import PostgresProvider


def test_build_database_provider_returns_postgres() -> None:
    settings = AppSettings()
    provider = build_database_provider(settings)
    assert isinstance(provider, PostgresProvider)


def test_build_database_provider_rejects_unsupported_driver(monkeypatch) -> None:
    monkeypatch.setenv("EITOHFORGE_DB_DRIVER", "mysql+pymysql")
    settings = AppSettings()
    with pytest.raises(ValueError):
        build_database_provider(settings)


def test_postgres_provider_dsn_encodes_credentials() -> None:
    settings = AppSettings()
    settings.database.username = "user@name"
    settings.database.password = "p@ss word"
    provider = PostgresProvider(settings=settings.database)
    dsn = provider.dsn()
    assert "user%40name" in dsn
    assert "p%40ss+word" in dsn


def test_postgres_provider_connect_uses_psycopg(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakePsycopg:
        @staticmethod
        def connect(**kwargs: object) -> object:
            captured.update(kwargs)
            return object()

    settings = AppSettings()
    provider = PostgresProvider(settings=settings.database)
    monkeypatch.setattr(provider, "_load_psycopg", lambda: FakePsycopg)
    connection = provider.connect()
    assert connection is not None
    assert captured["host"] == settings.database.host
    assert captured["dbname"] == settings.database.name


def test_postgres_provider_ping_returns_true(monkeypatch) -> None:
    class FakeCursor:
        def execute(self, _: str) -> None:
            return None

        def close(self) -> None:
            return None

    class FakeConnection:
        def cursor(self) -> FakeCursor:
            return FakeCursor()

        def close(self) -> None:
            return None

    settings = AppSettings()
    provider = PostgresProvider(settings=settings.database)
    monkeypatch.setattr(provider, "connect", lambda: FakeConnection())
    assert provider.ping() is True


def test_database_registry_contains_primary_by_default() -> None:
    settings = AppSettings()
    registry = build_database_registry(settings)
    assert registry.has("primary")
    primary = registry.get("primary")
    assert isinstance(primary, PostgresProvider)


def test_database_registry_includes_enabled_analytics_and_search(monkeypatch) -> None:
    monkeypatch.setenv("EITOHFORGE_DB_ANALYTICS_ENABLED", "true")
    monkeypatch.setenv("EITOHFORGE_DB_SEARCH_ENABLED", "true")
    settings = AppSettings()
    registry = build_database_registry(settings)
    assert registry.has("analytics")
    assert registry.has("search")
    assert isinstance(registry.get("analytics"), PostgresProvider)
    assert isinstance(registry.get("search"), PostgresProvider)

