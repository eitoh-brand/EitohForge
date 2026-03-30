"""Database provider factory."""

from eitohforge_sdk.core.config import AppSettings, DatabaseSettings
from eitohforge_sdk.infrastructure.database.providers import DatabaseProvider, PostgresProvider
from eitohforge_sdk.infrastructure.database.registry import DatabaseRegistry


def _build_provider_for_driver(driver: str, settings: DatabaseSettings) -> DatabaseProvider:
    if driver.startswith("postgresql"):
        return PostgresProvider(settings=settings)
    raise ValueError(f"Unsupported database driver: {driver}")


def build_database_provider(settings: AppSettings) -> DatabaseProvider:
    """Build a database provider from runtime settings."""
    driver = settings.database.driver.lower()
    return _build_provider_for_driver(driver, settings.database)


def build_database_registry(settings: AppSettings) -> DatabaseRegistry:
    """Build a role-based multi-database registry."""
    registry = DatabaseRegistry()
    registry.register("primary", build_database_provider(settings))

    if settings.database_analytics.enabled:
        registry.register(
            "analytics",
            _build_provider_for_driver(
                settings.database_analytics.driver.lower(), settings.database_analytics
            ),
        )
    if settings.database_search.enabled:
        registry.register(
            "search",
            _build_provider_for_driver(settings.database_search.driver.lower(), settings.database_search),
        )
    return registry

