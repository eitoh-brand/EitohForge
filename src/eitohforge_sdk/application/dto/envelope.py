"""Helpers for consistent JSON envelopes (`ApiResponse` / `ApiErrorResponse`)."""

from __future__ import annotations

from typing import TypeVar

from eitohforge_sdk.application.dto.error import ApiError, ApiErrorResponse
from eitohforge_sdk.application.dto.response import ApiResponse, PaginatedApiResponse, PaginationMeta

T = TypeVar("T")


def ok(data: T | None = None, *, message: str | None = None) -> ApiResponse[T]:
    """Success envelope with optional payload."""
    return ApiResponse(success=True, data=data, message=message)


def paginated(
    items: tuple[T, ...],
    *,
    total: int,
    page_size: int,
    next_cursor: str | None = None,
    message: str | None = None,
) -> PaginatedApiResponse[T]:
    """Paginated success envelope."""
    return PaginatedApiResponse(
        success=True,
        data=items,
        pagination=PaginationMeta(total=total, page_size=page_size, next_cursor=next_cursor),
        message=message,
    )


def err(*, code: str, message: str) -> ApiErrorResponse:
    """Typed error envelope."""
    return ApiErrorResponse(error=ApiError(code=code, message=message))
