"""Search provider primitives."""

from eitohforge_sdk.infrastructure.search.contracts import (
    SearchDocument,
    SearchHit,
    SearchProvider,
    SearchQuery,
    SearchResult,
)
from eitohforge_sdk.infrastructure.search.factory import build_search_provider
from eitohforge_sdk.infrastructure.search.memory import InMemorySearchProvider
from eitohforge_sdk.infrastructure.search.opensearch import OpenSearchProvider

__all__ = [
    "SearchDocument",
    "SearchQuery",
    "SearchHit",
    "SearchResult",
    "SearchProvider",
    "InMemorySearchProvider",
    "OpenSearchProvider",
    "build_search_provider",
]
