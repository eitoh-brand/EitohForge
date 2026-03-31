"""Meilisearch search provider (REST API via stdlib :mod:`urllib`)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from eitohforge_sdk.infrastructure.search.contracts import (
    SearchDocument,
    SearchHit,
    SearchQuery,
    SearchResult,
)


def _meili_score(hit: dict[str, Any]) -> float | None:
    for key in ("_rankingScore", "rankingScore"):
        v = hit.get(key)
        if v is not None:
            return float(v)
    return None


class MeilisearchProvider:
    """Search provider using Meilisearch HTTP API."""

    def __init__(
        self,
        *,
        base_url: str,
        index_prefix: str = "",
        api_key: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._index_prefix = index_prefix.strip()
        self._api_key = api_key
        self._timeout = timeout_seconds

    def _uid(self, index: str) -> str:
        base = f"{self._index_prefix}_{index}".strip("_") if self._index_prefix else index
        return base.replace("/", "_")

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_key:
            h["Authorization"] = f"Bearer {self._api_key}"
        return h

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base}{path}"
        req = Request(url, data=body, method=method, headers=self._headers())
        try:
            with urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read()
        except HTTPError as exc:
            raise RuntimeError(f"Meilisearch HTTP {exc.code}: {exc.reason}") from exc
        except URLError as exc:
            raise RuntimeError(f"Meilisearch request failed: {exc.reason}") from exc
        if not raw:
            return {}
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}

    def index(self, document: SearchDocument) -> None:
        uid = self._uid(document.index)
        doc_body = dict(document.body)
        doc_body["id"] = document.document_id
        payload = json.dumps([doc_body]).encode("utf-8")
        self._request("POST", f"/indexes/{uid}/documents", body=payload)

    def index_many(self, documents: Sequence[SearchDocument]) -> None:
        for doc in documents:
            self.index(doc)

    def delete(self, *, index: str, document_id: str) -> bool:
        uid = self._uid(index)
        path = f"/indexes/{uid}/documents/{document_id}"
        url = f"{self._base}{path}"
        req = Request(url, method="DELETE", headers=self._headers())
        try:
            with urlopen(req, timeout=self._timeout) as resp:
                _ = resp.read()
        except HTTPError as exc:
            if exc.code == 404:
                return False
            raise RuntimeError(f"Meilisearch HTTP {exc.code}: {exc.reason}") from exc
        except URLError as exc:
            raise RuntimeError(f"Meilisearch request failed: {exc.reason}") from exc
        return True

    def search(self, query: SearchQuery) -> SearchResult:
        uid = self._uid(query.index)
        body: dict[str, Any] = {
            "limit": max(0, query.limit),
            "offset": max(0, query.offset),
        }
        if query.text:
            body["q"] = query.text
        # Meilisearch filter DSL differs from OpenSearch; extend mapping when needed.
        payload = json.dumps(body).encode("utf-8")
        data = self._request("POST", f"/indexes/{uid}/search", body=payload)
        hits_raw = data.get("hits", [])
        if not isinstance(hits_raw, list):
            hits_raw = []
        total = data.get("estimatedTotalHits")
        if not isinstance(total, int):
            total = len(hits_raw)
        hits = tuple(
            SearchHit(
                index=query.index,
                document_id=str(h.get("id", "")),
                score=_meili_score(h),
                body={k: v for k, v in h.items() if k not in {"id", "_rankingScore", "rankingScore"}},
            )
            for h in hits_raw
            if isinstance(h, dict)
        )
        took = data.get("processingTimeMs")
        return SearchResult(
            total=total,
            hits=hits,
            took_ms=int(took) if isinstance(took, int) else None,
        )

    def ping(self) -> bool:
        try:
            self._request("GET", "/health")
            return True
        except RuntimeError:
            return False
