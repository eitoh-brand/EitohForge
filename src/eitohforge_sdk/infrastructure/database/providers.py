"""Database provider interfaces and Postgres adapter baseline."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
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

