"""Tenant-scoped cache provider wrappers.

Phase 18: tenant cache namespace.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from eitohforge_sdk.core.tenant import TenantContext
from eitohforge_sdk.infrastructure.cache.contracts import CacheProvider


@dataclass(frozen=True)
class TenantScopedCacheProvider:
    """Prefix cache keys with the current tenant id (best-effort)."""

    delegate: CacheProvider
    separator: str = ":"

    def _namespaced_key(self, key: str) -> str:
        tenant_id = TenantContext.current().tenant_id
        if tenant_id is None:
            return key
        tenant_prefix = f"{tenant_id}{self.separator}"
        # Avoid double-prefixing when callers already include the tenant segment.
        if key.startswith(tenant_prefix):
            return key
        return f"{tenant_prefix}{key}"

    def get(self, key: str) -> Any | None:
        return self.delegate.get(self._namespaced_key(key))

    def set(self, key: str, value: Any, *, ttl_seconds: int | None = None) -> None:
        self.delegate.set(self._namespaced_key(key), value, ttl_seconds=ttl_seconds)

    def delete(self, key: str) -> bool:
        return self.delegate.delete(self._namespaced_key(key))

    def exists(self, key: str) -> bool:
        return self.delegate.exists(self._namespaced_key(key))

