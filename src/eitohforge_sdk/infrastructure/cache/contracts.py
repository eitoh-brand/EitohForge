"""Cache provider contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class CacheEntry:
    """Cache value container."""

    key: str
    value: Any
    expires_at: datetime | None = None


class CacheProvider(Protocol):
    """Cache provider interface."""

    def get(self, key: str) -> Any | None:
        ...

    def set(self, key: str, value: Any, *, ttl_seconds: int | None = None) -> None:
        ...

    def delete(self, key: str) -> bool:
        ...

    def exists(self, key: str) -> bool:
        ...

