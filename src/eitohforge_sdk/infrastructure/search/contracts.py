"""Search provider contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class SearchDocument:
    """Indexable document payload."""

    index: str
    document_id: str
    body: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchQuery:
    """Search query envelope."""

    index: str
    text: str | None = None
    filters: Mapping[str, Any] = field(default_factory=dict)
    offset: int = 0
    limit: int = 20


@dataclass(frozen=True)
class SearchHit:
    """Single search hit."""

    index: str
    document_id: str
    score: float | None
    body: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResult:
    """Search result payload."""

    total: int
    hits: tuple[SearchHit, ...]
    took_ms: int | None = None


class SearchProvider(Protocol):
    """Search backend provider interface."""

    def index(self, document: SearchDocument) -> None:
        ...

    def index_many(self, documents: Sequence[SearchDocument]) -> None:
        ...

    def delete(self, *, index: str, document_id: str) -> bool:
        ...

    def search(self, query: SearchQuery) -> SearchResult:
        ...

    def ping(self) -> bool:
        ...
