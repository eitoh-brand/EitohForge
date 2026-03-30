"""Unified API response DTO models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


TResponseData = TypeVar("TResponseData")


class ApiResponseMeta(BaseModel):
    """Standard metadata attached to all API responses."""

    model_config = ConfigDict(frozen=True)

    request_id: str | None = None
    trace_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PaginationMeta(BaseModel):
    """Pagination envelope metadata for list responses."""

    model_config = ConfigDict(frozen=True)

    total: int = Field(ge=0)
    page_size: int = Field(ge=1)
    next_cursor: str | None = None


class ApiResponse(BaseModel, Generic[TResponseData]):
    """Unified non-paginated API response format."""

    model_config = ConfigDict(frozen=True)

    success: bool = True
    data: TResponseData | None = None
    message: str | None = None
    meta: ApiResponseMeta = Field(default_factory=ApiResponseMeta)


class PaginatedApiResponse(BaseModel, Generic[TResponseData]):
    """Unified paginated API response format."""

    model_config = ConfigDict(frozen=True)

    success: bool = True
    data: tuple[TResponseData, ...] = ()
    pagination: PaginationMeta
    message: str | None = None
    meta: ApiResponseMeta = Field(default_factory=ApiResponseMeta)

