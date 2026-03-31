"""Named SQLAlchemy engine registry for multi-database / read-replica routing."""

from __future__ import annotations

from typing import Any


class EngineRegistry:
    """Hold multiple named engines (primary, analytics, search, read replicas, etc.).

    For logical database *roles* with ``DatabaseProvider``, see
    ``eitohforge_sdk.infrastructure.database.registry.DatabaseRegistry``.
    """

    def __init__(self) -> None:
        self._engines: dict[str, Any] = {}

    def register(self, name: str, engine: Any) -> None:
        if not name.strip():
            raise ValueError("Engine name is required.")
        self._engines[name.strip()] = engine

    def get(self, name: str) -> Any:
        key = name.strip()
        if key not in self._engines:
            raise KeyError(f"Unknown database engine: {key}")
        return self._engines[key]

    def optional(self, name: str) -> Any | None:
        return self._engines.get(name.strip())

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._engines.keys()))
