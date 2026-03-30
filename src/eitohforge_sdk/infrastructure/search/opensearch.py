"""OpenSearch/Elasticsearch search provider adapter."""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from typing import Any, cast

from eitohforge_sdk.infrastructure.search.contracts import (
    SearchDocument,
    SearchHit,
    SearchQuery,
    SearchResult,
)


class OpenSearchProvider:
    """Search provider backed by OpenSearch or Elasticsearch APIs."""

    def __init__(
        self,
        *,
        hosts: tuple[str, ...],
        index_prefix: str = "",
        username: str | None = None,
        password: str | None = None,
        verify_certs: bool = True,
        client: Any | None = None,
    ) -> None:
        self._hosts = hosts
        self._index_prefix = index_prefix.strip()
        self._username = username
        self._password = password
        self._verify_certs = verify_certs
        self._client = client or self._build_client()

    def index(self, document: SearchDocument) -> None:
        self._client.index(
            index=self._prefixed_index(document.index),
            id=document.document_id,
            body=dict(document.body),
            refresh=False,
        )

    def index_many(self, documents: Sequence[SearchDocument]) -> None:
        for document in documents:
            self.index(document)

    def delete(self, *, index: str, document_id: str) -> bool:
        try:
            response = self._client.delete(index=self._prefixed_index(index), id=document_id, refresh=False)
        except Exception as exc:
            if exc.__class__.__name__ == "NotFoundError":
                return False
            raise
        result = str(response.get("result", "")).lower()
        return result in {"deleted", "not_found"}

    def search(self, query: SearchQuery) -> SearchResult:
        response = self._client.search(
            index=self._prefixed_index(query.index),
            body=self._build_query_body(query),
            from_=max(0, query.offset),
            size=max(0, query.limit),
        )
        hits_payload = cast(dict[str, Any], response.get("hits", {}))
        raw_hits = cast(list[dict[str, Any]], hits_payload.get("hits", []))
        total_payload = hits_payload.get("total", 0)
        total = total_payload.get("value", 0) if isinstance(total_payload, dict) else int(total_payload)
        hits = tuple(
            SearchHit(
                index=self._strip_prefix(str(hit.get("_index", query.index))),
                document_id=str(hit.get("_id", "")),
                score=float(hit["_score"]) if hit.get("_score") is not None else None,
                body=cast(dict[str, Any], hit.get("_source", {})),
            )
            for hit in raw_hits
        )
        took = response.get("took")
        return SearchResult(total=total, hits=hits, took_ms=int(took) if isinstance(took, int) else None)

    def ping(self) -> bool:
        return bool(self._client.ping())

    def _build_client(self) -> Any:
        kwargs: dict[str, Any] = {"hosts": list(self._hosts)}
        if self._username:
            kwargs["http_auth"] = (
                self._username,
                self._password or "",
            )
            kwargs["basic_auth"] = (self._username, self._password or "")
        kwargs["verify_certs"] = self._verify_certs

        try:
            opensearch_module = importlib.import_module("opensearchpy")
            return opensearch_module.OpenSearch(**kwargs)
        except ModuleNotFoundError:
            pass

        try:
            elastic_module = importlib.import_module("elasticsearch")
            return elastic_module.Elasticsearch(**kwargs)
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Search provider requires 'opensearch-py' or 'elasticsearch'. "
                "Install one via `pip install opensearch-py`."
            ) from exc

    def _prefixed_index(self, index: str) -> str:
        if not self._index_prefix:
            return index
        return f"{self._index_prefix}-{index}"

    def _strip_prefix(self, index: str) -> str:
        prefix = f"{self._index_prefix}-" if self._index_prefix else ""
        if prefix and index.startswith(prefix):
            return index[len(prefix) :]
        return index

    @staticmethod
    def _build_query_body(query: SearchQuery) -> dict[str, Any]:
        must: list[dict[str, Any]] = []
        if query.text and query.text.strip():
            must.append(
                {
                    "multi_match": {
                        "query": query.text.strip(),
                        "fields": ["*"],
                    }
                }
            )

        filters: list[dict[str, Any]] = []
        for field_name, value in query.filters.items():
            if not field_name.strip():
                continue
            filters.append({"term": {field_name: value}})

        bool_query: dict[str, Any] = {}
        if must:
            bool_query["must"] = must
        if filters:
            bool_query["filter"] = filters
        if not bool_query:
            return {"query": {"match_all": {}}}
        return {"query": {"bool": bool_query}}
