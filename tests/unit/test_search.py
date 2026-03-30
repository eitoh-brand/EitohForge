from __future__ import annotations

from eitohforge_sdk.core.config import AppSettings, SearchSettings
from eitohforge_sdk.infrastructure.search import (
    InMemorySearchProvider,
    OpenSearchProvider,
    SearchDocument,
    SearchQuery,
    build_search_provider,
)


def test_in_memory_search_provider_indexes_and_filters() -> None:
    provider = InMemorySearchProvider()
    provider.index(
        SearchDocument(
            index="orders",
            document_id="ord_1",
            body={"title": "Coffee order", "tenant_id": "t1"},
        )
    )
    provider.index(
        SearchDocument(
            index="orders",
            document_id="ord_2",
            body={"title": "Tea order", "tenant_id": "t2"},
        )
    )
    result = provider.search(
        SearchQuery(index="orders", text="coffee", filters={"tenant_id": "t1"}, limit=10)
    )
    assert result.total == 1
    assert len(result.hits) == 1
    assert result.hits[0].document_id == "ord_1"


def test_build_search_provider_returns_memory_for_memory_mode() -> None:
    settings = AppSettings(search=SearchSettings(enabled=True, provider="memory"))
    provider = build_search_provider(settings)
    assert isinstance(provider, InMemorySearchProvider)


def test_build_search_provider_returns_opensearch_for_external_modes() -> None:
    class FakeClient:
        def index(self, **_: object) -> None:
            return None

        def delete(self, **_: object) -> dict[str, str]:
            return {"result": "deleted"}

        def search(self, **_: object) -> dict[str, object]:
            return {"hits": {"total": {"value": 0}, "hits": []}, "took": 1}

        def ping(self) -> bool:
            return True

    settings = AppSettings(
        search=SearchSettings(
            enabled=True,
            provider="opensearch",
            hosts="https://search.example.com",
            index_prefix="forge",
        )
    )
    provider = build_search_provider(settings, client=FakeClient())
    assert isinstance(provider, OpenSearchProvider)
    assert provider.ping() is True
