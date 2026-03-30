"""Cache-layer scaffold template fragments."""

CACHE_FILE_TEMPLATES: dict[str, str] = {
    "app/infrastructure/cache/__init__.py": """from app.infrastructure.cache.contracts import CacheEntry, CacheProvider
from app.infrastructure.cache.factory import build_cache_provider
from app.infrastructure.cache.invalidation import AdvancedCacheProvider
from app.infrastructure.cache.memory import MemoryCacheProvider
from app.infrastructure.cache.redis import RedisCacheProvider
""",
    "app/infrastructure/cache/contracts.py": """from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class CacheEntry:
    key: str
    value: Any
    expires_at: datetime | None = None


class CacheProvider(Protocol):
    def get(self, key: str) -> Any | None:
        ...

    def set(self, key: str, value: Any, *, ttl_seconds: int | None = None) -> None:
        ...

    def delete(self, key: str) -> bool:
        ...

    def exists(self, key: str) -> bool:
        ...
""",
    "app/infrastructure/cache/memory.py": """from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from app.infrastructure.cache.contracts import CacheEntry


@dataclass
class MemoryCacheProvider:
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
""",
    "app/infrastructure/cache/redis.py": """from __future__ import annotations

import importlib
import json
from typing import Any, cast


class RedisCacheProvider:
    def __init__(self, *, redis_url: str, key_prefix: str = "eitohforge:cache", client: Any | None = None) -> None:
        self._key_prefix = key_prefix
        self._client = client or self._build_client(redis_url)

    def get(self, key: str) -> Any | None:
        raw = cast(str | None, self._client.get(self._cache_key(key)))
        if raw is None:
            return None
        return json.loads(raw)

    def set(self, key: str, value: Any, *, ttl_seconds: int | None = None) -> None:
        payload = json.dumps(value, separators=(",", ":"), sort_keys=True)
        cache_key = self._cache_key(key)
        if ttl_seconds is None:
            self._client.set(cache_key, payload)
        else:
            self._client.setex(cache_key, ttl_seconds, payload)

    def delete(self, key: str) -> bool:
        deleted = int(self._client.delete(self._cache_key(key)))
        return deleted > 0

    def exists(self, key: str) -> bool:
        return bool(self._client.exists(self._cache_key(key)))

    def _cache_key(self, key: str) -> str:
        return f"{self._key_prefix}:{key}"

    @staticmethod
    def _build_client(redis_url: str) -> Any:
        try:
            redis_module = importlib.import_module("redis")
        except ModuleNotFoundError as exc:
            raise RuntimeError("Redis cache provider requires 'redis'. Install via `pip install redis`.") from exc
        return redis_module.Redis.from_url(redis_url, decode_responses=True)
""",
    "app/infrastructure/cache/factory.py": """from typing import Any

from app.core.config import AppSettings, CacheSettings
from app.infrastructure.cache.contracts import CacheProvider
from app.infrastructure.cache.memory import MemoryCacheProvider
from app.infrastructure.cache.redis import RedisCacheProvider


def build_cache_provider(
    settings: AppSettings,
    *,
    redis_client: Any | None = None,
) -> CacheProvider:
    return _build_cache_provider_for_settings(settings.cache, redis_client=redis_client)


def _build_cache_provider_for_settings(
    settings: CacheSettings,
    *,
    redis_client: Any | None,
) -> CacheProvider:
    provider = settings.provider.lower()
    if provider == "memory":
        return MemoryCacheProvider()
    if provider == "redis":
        return RedisCacheProvider(redis_url=settings.redis_url, client=redis_client)
    raise ValueError(f"Unsupported cache provider: {settings.provider}")
""",
    "app/infrastructure/cache/invalidation.py": """from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from app.infrastructure.cache.contracts import CacheProvider


@dataclass
class AdvancedCacheProvider:
    delegate: CacheProvider
    _known_keys: set[str] = field(default_factory=set)
    _tags_to_keys: dict[str, set[str]] = field(default_factory=dict)
    _keys_to_tags: dict[str, set[str]] = field(default_factory=dict)

    def get(self, key: str) -> Any | None:
        return self.delegate.get(key)

    def set(self, key: str, value: Any, *, ttl_seconds: int | None = None) -> None:
        self._known_keys.add(key)
        self._detach_key_from_tags(key)
        self.delegate.set(key, value, ttl_seconds=ttl_seconds)

    def set_with_tags(
        self,
        key: str,
        value: Any,
        *,
        tags: tuple[str, ...] = (),
        ttl_seconds: int | None = None,
    ) -> None:
        normalized_tags = tuple(tag.strip().lower() for tag in tags if tag.strip())
        self.set(key, value, ttl_seconds=ttl_seconds)
        if not normalized_tags:
            return
        key_tags = self._keys_to_tags.setdefault(key, set())
        for tag in normalized_tags:
            self._tags_to_keys.setdefault(tag, set()).add(key)
            key_tags.add(tag)

    def delete(self, key: str) -> bool:
        deleted = self.delegate.delete(key)
        if deleted:
            self._known_keys.discard(key)
            self._detach_key_from_tags(key)
        return deleted

    def exists(self, key: str) -> bool:
        return self.delegate.exists(key)

    def invalidate_tag(self, tag: str) -> int:
        normalized_tag = tag.strip().lower()
        if not normalized_tag:
            return 0
        keys = tuple(self._tags_to_keys.get(normalized_tag, set()))
        return self.invalidate_keys(keys)

    def invalidate_prefix(self, prefix: str) -> int:
        normalized_prefix = prefix.strip()
        if not normalized_prefix:
            return 0
        keys = tuple(key for key in self._known_keys if key.startswith(normalized_prefix))
        return self.invalidate_keys(keys)

    def invalidate_keys(self, keys: Iterable[str]) -> int:
        deleted = 0
        for key in keys:
            if self.delete(key):
                deleted += 1
        return deleted

    def write_through(
        self,
        key: str,
        value: Any,
        *,
        tags: tuple[str, ...] = (),
        ttl_seconds: int | None = None,
        invalidate_prefixes: tuple[str, ...] = (),
    ) -> Any:
        for prefix in invalidate_prefixes:
            self.invalidate_prefix(prefix)
        self.set_with_tags(key, value, tags=tags, ttl_seconds=ttl_seconds)
        return value

    def _detach_key_from_tags(self, key: str) -> None:
        tags = self._keys_to_tags.pop(key, set())
        for tag in tags:
            keys = self._tags_to_keys.get(tag)
            if keys is None:
                continue
            keys.discard(key)
            if not keys:
                self._tags_to_keys.pop(tag, None)
""",
}

