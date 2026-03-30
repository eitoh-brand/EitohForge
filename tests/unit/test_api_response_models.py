from __future__ import annotations

from datetime import datetime

from eitohforge_sdk.application.dto import (
    ApiResponse,
    ApiResponseMeta,
    PaginatedApiResponse,
    PaginationMeta,
)


def test_api_response_default_shape() -> None:
    response = ApiResponse[dict[str, str]](data={"status": "ok"})
    assert response.success is True
    assert response.data == {"status": "ok"}
    assert isinstance(response.meta, ApiResponseMeta)
    assert isinstance(response.meta.timestamp, datetime)


def test_paginated_api_response_shape() -> None:
    response = PaginatedApiResponse[str](
        data=("a", "b"),
        pagination=PaginationMeta(total=10, page_size=2, next_cursor="2"),
    )
    assert response.success is True
    assert response.data == ("a", "b")
    assert response.pagination.total == 10
    assert response.pagination.page_size == 2
    assert response.pagination.next_cursor == "2"

