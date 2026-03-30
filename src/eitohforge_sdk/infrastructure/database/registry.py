"""Database registry for multi-database access."""

from __future__ import annotations

from dataclasses import dataclass, field

from eitohforge_sdk.infrastructure.database.providers import DatabaseProvider


@dataclass
class DatabaseRegistry:
    """Registry that stores providers by logical database role."""

    _providers: dict[str, DatabaseProvider] = field(default_factory=dict)

    def register(self, role: str, provider: DatabaseProvider) -> None:
        """Register a provider for a specific role."""
        self._providers[role] = provider

    def get(self, role: str) -> DatabaseProvider:
        """Return provider for role or raise when missing."""
        if role not in self._providers:
            raise KeyError(f"No database provider registered for role: {role}")
        return self._providers[role]

    def has(self, role: str) -> bool:
        """Return whether a role is registered."""
        return role in self._providers

    def roles(self) -> tuple[str, ...]:
        """Return registered role names."""
        return tuple(sorted(self._providers.keys()))

