"""In-memory search provider."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from eitohforge_sdk.infrastructure.search.contracts import (
    SearchDocument,
    SearchHit,
    SearchQuery,
    SearchResult,
)


@dataclass
class InMemorySearchProvider:
    """Simple in-memory search provider for local/dev use."""

    _documents: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)

    def index(self, document: SearchDocument) -> None:
        bucket = self._documents.setdefault(document.index, {})
        bucket[document.document_id] = dict(document.body)

    def index_many(self, documents: Sequence[SearchDocument]) -> None:
        for document in documents:
            self.index(document)

    def delete(self, *, index: str, document_id: str) -> bool:
        bucket = self._documents.get(index)
        if bucket is None:
            return False
        return bucket.pop(document_id, None) is not None

    def search(self, query: SearchQuery) -> SearchResult:
        bucket = self._documents.get(query.index, {})
        hits: list[SearchHit] = []
        normalized_text = (query.text or "").strip().lower()
        normalized_filters = _normalize_filters(query.filters)

        for document_id, body in bucket.items():
            if normalized_text and normalized_text not in _flatten_text(body):
                continue
            if normalized_filters and not _matches_filters(body, normalized_filters):
                continue
            hits.append(
                SearchHit(
                    index=query.index,
                    document_id=document_id,
                    score=1.0 if normalized_text else None,
                    body=dict(body),
                )
            )

        total = len(hits)
        start = max(0, query.offset)
        end = max(start, start + max(0, query.limit))
        return SearchResult(total=total, hits=tuple(hits[start:end]), took_ms=0)

    def ping(self) -> bool:
        return True


def _matches_filters(body: Mapping[str, Any], filters: Mapping[str, Any]) -> bool:
    for key, expected in filters.items():
        if body.get(key) != expected:
            return False
    return True


def _flatten_text(payload: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for value in payload.values():
        if isinstance(value, str):
            parts.append(value.lower())
        elif isinstance(value, (int, float, bool)):
            parts.append(str(value).lower())
        elif isinstance(value, Mapping):
            parts.append(_flatten_text(value))
        elif isinstance(value, (list, tuple)):
            parts.extend(str(item).lower() for item in value)
    return " ".join(parts)


def _normalize_filters(filters: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in filters.items() if key.strip()}
