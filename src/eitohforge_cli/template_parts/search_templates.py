"""Search infrastructure template fragments."""

SEARCH_FILE_TEMPLATES: dict[str, str] = {
    "app/infrastructure/search/__init__.py": """from app.infrastructure.search.contracts import (
    SearchDocument,
    SearchHit,
    SearchProvider,
    SearchQuery,
    SearchResult,
)
from app.infrastructure.search.factory import build_search_provider
from app.infrastructure.search.memory import InMemorySearchProvider
from app.infrastructure.search.opensearch import OpenSearchProvider
""",
    "app/infrastructure/search/contracts.py": """from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class SearchDocument:
    index: str
    document_id: str
    body: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchQuery:
    index: str
    text: str | None = None
    filters: Mapping[str, Any] = field(default_factory=dict)
    offset: int = 0
    limit: int = 20


@dataclass(frozen=True)
class SearchHit:
    index: str
    document_id: str
    score: float | None
    body: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResult:
    total: int
    hits: tuple[SearchHit, ...]
    took_ms: int | None = None


class SearchProvider(Protocol):
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
""",
    "app/infrastructure/search/memory.py": """from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from app.infrastructure.search.contracts import SearchDocument, SearchHit, SearchQuery, SearchResult


@dataclass
class InMemorySearchProvider:
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
""",
    "app/infrastructure/search/opensearch.py": """import importlib
from collections.abc import Sequence
from typing import Any, cast

from app.infrastructure.search.contracts import SearchDocument, SearchHit, SearchQuery, SearchResult


class OpenSearchProvider:
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
            kwargs["http_auth"] = (self._username, self._password or "")
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
""",
    "app/infrastructure/search/factory.py": """from typing import Any

from app.core.config import AppSettings, SearchSettings
from app.infrastructure.search.contracts import SearchProvider
from app.infrastructure.search.memory import InMemorySearchProvider
from app.infrastructure.search.opensearch import OpenSearchProvider


def build_search_provider(
    settings: AppSettings,
    *,
    client: Any | None = None,
) -> SearchProvider:
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
""",
}
