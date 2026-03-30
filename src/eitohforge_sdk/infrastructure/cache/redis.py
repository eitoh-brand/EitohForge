"""Redis cache provider."""

from __future__ import annotations

import importlib
import json
from typing import Any, cast


class RedisCacheProvider:
    """Redis-backed cache provider with JSON serialization."""

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

