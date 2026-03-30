"""In-memory cache provider."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from eitohforge_sdk.infrastructure.cache.contracts import CacheEntry


@dataclass
class MemoryCacheProvider:
    """In-memory cache with optional TTL support."""

    _entries: dict[str, CacheEntry] = field(default_factory=dict)

    def get(self, key: str) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if self._is_expired(entry):
            self._entries.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: Any, *, ttl_seconds: int | None = None) -> None:
        expires_at = None
        if ttl_seconds is not None:
            expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        self._entries[key] = CacheEntry(key=key, value=value, expires_at=expires_at)

    def delete(self, key: str) -> bool:
        return self._entries.pop(key, None) is not None

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    @staticmethod
    def _is_expired(entry: CacheEntry) -> bool:
        if entry.expires_at is None:
            return False
        return entry.expires_at <= datetime.now(UTC)

