"""Map logical repository names to database registry roles (multi-DB routing)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RepositoryBindingMap:
    """Bind domain repository identifiers to ``DatabaseRegistry`` role names.

    Example: ``orders`` → ``primary``, ``audit`` → ``analytics``.
    """

    _logical_to_role: dict[str, str] = field(default_factory=dict)

    def bind(self, logical_name: str, database_role: str) -> None:
        """Register a logical repository name against a database role."""
        key = logical_name.strip()
        role = database_role.strip()
        if not key or not role:
            raise ValueError("logical_name and database_role must be non-empty.")
        self._logical_to_role[key] = role

    def resolve(self, logical_name: str) -> str:
        """Return the database role for a logical name."""
        key = logical_name.strip()
        if key not in self._logical_to_role:
            raise KeyError(f"No repository binding registered for {logical_name!r}.")
        return self._logical_to_role[key]

    def resolve_or(self, logical_name: str, default_role: str) -> str:
        """Return bound role or ``default_role`` when unmapped."""
        key = logical_name.strip()
        return self._logical_to_role.get(key, default_role.strip())

    def names(self) -> tuple[str, ...]:
        """Registered logical repository names."""
        return tuple(sorted(self._logical_to_role.keys()))
