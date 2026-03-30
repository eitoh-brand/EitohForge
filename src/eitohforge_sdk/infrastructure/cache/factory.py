"""Cache provider factory."""

from __future__ import annotations

from typing import Any

from eitohforge_sdk.core.config import AppSettings, CacheSettings
from eitohforge_sdk.infrastructure.cache.contracts import CacheProvider
from eitohforge_sdk.infrastructure.cache.memory import MemoryCacheProvider
from eitohforge_sdk.infrastructure.cache.redis import RedisCacheProvider
from eitohforge_sdk.infrastructure.cache.tenant_scoped import TenantScopedCacheProvider


def build_cache_provider(
    settings: AppSettings,
    *,
    redis_client: Any | None = None,
) -> CacheProvider:
    """Build a cache provider from app settings."""
    delegate = _build_cache_provider_for_settings(settings.cache, redis_client=redis_client)
    if settings.tenant.enabled:
        return TenantScopedCacheProvider(delegate=delegate)
    return delegate


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

