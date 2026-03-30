from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from eitohforge_sdk.core.config import AppSettings
from eitohforge_sdk.infrastructure.cache import (
    MemoryCacheProvider,
    RedisCacheProvider,
    build_cache_provider,
)
from eitohforge_sdk.infrastructure.cache.contracts import CacheEntry


def test_memory_cache_provider_get_set_delete_exists() -> None:
    provider = MemoryCacheProvider()
    provider.set("k1", {"a": 1})
    assert provider.get("k1") == {"a": 1}
    assert provider.exists("k1") is True
    assert provider.delete("k1") is True
    assert provider.get("k1") is None
    assert provider.exists("k1") is False


def test_memory_cache_provider_expires_entries() -> None:
    provider = MemoryCacheProvider(
        _entries={"k1": CacheEntry(key="k1", value="v1", expires_at=datetime.now(UTC) - timedelta(seconds=1))}
    )
    assert provider.get("k1") is None
    assert provider.exists("k1") is False


class _FakeRedisClient:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str) -> None:
        self._store[key] = value

    def setex(self, key: str, ttl: int, value: str) -> None:
        _ = ttl
        self._store[key] = value

    def delete(self, key: str) -> int:
        return 1 if self._store.pop(key, None) is not None else 0

    def exists(self, key: str) -> int:
        return 1 if key in self._store else 0


def test_redis_cache_provider_json_roundtrip() -> None:
    provider = RedisCacheProvider(redis_url="redis://localhost:6379/0", client=_FakeRedisClient())
    payload: dict[str, Any] = {"name": "acme", "count": 2}
    provider.set("key", payload, ttl_seconds=30)
    assert provider.get("key") == payload
    assert provider.exists("key") is True
    assert provider.delete("key") is True
    assert provider.get("key") is None


def test_build_cache_provider_uses_settings() -> None:
    memory_settings = AppSettings(cache={"provider": "memory"})
    memory_provider = build_cache_provider(memory_settings)
    assert isinstance(memory_provider, MemoryCacheProvider)

    redis_settings = AppSettings(cache={"provider": "redis"})
    redis_provider = build_cache_provider(redis_settings, redis_client=_FakeRedisClient())
    assert isinstance(redis_provider, RedisCacheProvider)

