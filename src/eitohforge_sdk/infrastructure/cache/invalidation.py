"""Advanced cache invalidation helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from eitohforge_sdk.infrastructure.cache.contracts import CacheProvider


@dataclass
class AdvancedCacheProvider:
    """Cache wrapper adding tag/prefix invalidation and write-through semantics."""

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
        """Invalidate related prefixes and immediately write latest value to cache."""
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

