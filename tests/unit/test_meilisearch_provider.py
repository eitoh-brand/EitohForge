from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

from eitohforge_sdk.infrastructure.search.contracts import SearchDocument, SearchQuery
from eitohforge_sdk.infrastructure.search.meilisearch import MeilisearchProvider


def test_meilisearch_search_maps_hits() -> None:
    provider = MeilisearchProvider(base_url="http://localhost:7700", index_prefix="pfx")
    fake_response = {
        "hits": [{"id": "a1", "title": "Hello", "_rankingScore": 0.9}],
        "estimatedTotalHits": 1,
        "processingTimeMs": 3,
    }
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value.read.return_value = json.dumps(fake_response).encode("utf-8")
    mock_cm.__exit__.return_value = None

    with patch("eitohforge_sdk.infrastructure.search.meilisearch.urlopen", return_value=mock_cm):
        result = provider.search(SearchQuery(index="docs", text="hello", limit=10))

    assert result.total == 1
    assert len(result.hits) == 1
    assert result.hits[0].document_id == "a1"
    assert result.hits[0].score == 0.9
    assert result.took_ms == 3


def test_meilisearch_index_posts_documents() -> None:
    provider = MeilisearchProvider(base_url="http://localhost:7700", index_prefix="p")
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value.read.return_value = b"{}"
    mock_cm.__exit__.return_value = None

    with patch("eitohforge_sdk.infrastructure.search.meilisearch.urlopen", return_value=mock_cm) as m:
        provider.index(SearchDocument(index="docs", document_id="x1", body={"title": "t"}))

    assert m.called
    req = m.call_args[0][0]
    assert req.get_method() == "POST"
    assert "/indexes/p_docs/documents" in req.get_full_url()


def test_meilisearch_delete_404_returns_false() -> None:
    from urllib.error import HTTPError

    provider = MeilisearchProvider(base_url="http://localhost:7700")
    err = HTTPError("http://x", 404, "n", hdrs=None, fp=BytesIO(b""))

    with patch("eitohforge_sdk.infrastructure.search.meilisearch.urlopen", side_effect=err):
        assert provider.delete(index="docs", document_id="missing") is False
