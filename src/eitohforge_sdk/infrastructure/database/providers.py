"""Database provider interfaces and SQL adapters (Postgres, MySQL, SQLite)."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import sqlite3
from typing import Any, Protocol

from eitohforge_sdk.core.config import DatabaseSettings


class DatabaseProvider(Protocol):
    """Contract for concrete database providers."""

    name: str

    def dsn(self) -> str:
        """Return connection DSN for this provider."""

    def connect(self) -> Any:
        """Create a driver connection object."""

    def ping(self) -> bool:
        """Return whether provider can establish a healthy connection."""


@dataclass
class PostgresProvider:
    """Postgres database adapter."""

    settings: DatabaseSettings
    connect_timeout_seconds: int = 5
    name: str = "postgres"

    def dsn(self) -> str:
        """Build postgres DSN using configured driver."""
        return self.settings.sqlalchemy_url

    def connect(self) -> Any:
        """Open a psycopg connection using current settings."""
        psycopg = self._load_psycopg()
        return psycopg.connect(
            host=self.settings.host,
            port=self.settings.port,
            user=self.settings.username,
            password=self.settings.password,
            dbname=self.settings.name,
            connect_timeout=self.connect_timeout_seconds,
        )

    def ping(self) -> bool:
        """Check connectivity by running a trivial query."""
        try:
            connection = self.connect()
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            connection.close()
        except Exception:
            return False
        return True

    @staticmethod
    def _load_psycopg() -> Any:
        try:
            return importlib.import_module("psycopg")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Postgres provider requires 'psycopg'. Install it with: pip install psycopg[binary]"
            ) from exc


@dataclass
class MySQLProvider:
    """MySQL database adapter using ``pymysql`` (sync)."""

    settings: DatabaseSettings
    connect_timeout_seconds: int = 5
    name: str = "mysql"

    def dsn(self) -> str:
        """Build SQLAlchemy-compatible MySQL URL (``mysql+pymysql`` or configured driver)."""
        return self.settings.sqlalchemy_url

    def connect(self) -> Any:
        """Open a PyMySQL connection using current settings."""
        pymysql = self._load_pymysql()
        return pymysql.connect(
            host=self.settings.host,
            port=self.settings.port,
            user=self.settings.username,
            password=self.settings.password,
            database=self.settings.name,
            connect_timeout=self.connect_timeout_seconds,
        )

    def ping(self) -> bool:
        """Check connectivity by running a trivial query."""
        try:
            connection = self.connect()
            try:
                cursor = connection.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
            finally:
                connection.close()
        except Exception:
            return False
        return True

    @staticmethod
    def _load_pymysql() -> Any:
        try:
            return importlib.import_module("pymysql")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "MySQL provider requires 'pymysql'. Install it with: pip install pymysql"
            ) from exc


@dataclass
class SqliteProvider:
    """SQLite database adapter (stdlib ``sqlite3``); ``DatabaseSettings.name`` is file path or ``:memory:``."""

    settings: DatabaseSettings
    name: str = "sqlite"

    def dsn(self) -> str:
        """Return SQLAlchemy-compatible SQLite URL (sync ``pysqlite`` driver)."""
        return self.settings.sqlalchemy_url

    def connect(self) -> sqlite3.Connection:
        """Open a SQLite connection."""
        db = self.settings.name.strip()
        if db == ":memory:":
            return sqlite3.connect(":memory:")
        return sqlite3.connect(db)

    def ping(self) -> bool:
        """Check connectivity by running a trivial query."""
        try:
            connection = self.connect()
            try:
                connection.execute("SELECT 1").fetchone()
            finally:
                connection.close()
        except Exception:
            return False
        return True
