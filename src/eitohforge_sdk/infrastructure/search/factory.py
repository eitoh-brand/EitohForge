"""Search provider factory."""

from __future__ import annotations

from typing import Any

from eitohforge_sdk.core.config import AppSettings, SearchSettings
from eitohforge_sdk.infrastructure.search.contracts import SearchProvider
from eitohforge_sdk.infrastructure.search.memory import InMemorySearchProvider
from eitohforge_sdk.infrastructure.search.opensearch import OpenSearchProvider


def build_search_provider(
    settings: AppSettings,
    *,
    client: Any | None = None,
) -> SearchProvider:
    """Build a search provider from app settings."""
    return _build_search_provider_for_settings(settings.search, client=client)


def _build_search_provider_for_settings(
    settings: SearchSettings,
    *,
    client: Any | None,
) -> SearchProvider:
    provider = settings.provider.lower()
    if provider == "memory":
        return InMemorySearchProvider()
    if provider in {"opensearch", "elasticsearch"}:
        hosts = tuple(part.strip() for part in settings.hosts.split(",") if part.strip())
        if not hosts:
            raise ValueError("Search hosts must include at least one host URL.")
        return OpenSearchProvider(
            hosts=hosts,
            index_prefix=settings.index_prefix,
            username=settings.username,
            password=settings.password,
            verify_certs=settings.verify_tls,
            client=client,
        )
    raise ValueError(f"Unsupported search provider: {settings.provider}")
