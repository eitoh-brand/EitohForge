"""Standardized API error response DTO models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from eitohforge_sdk.application.dto.response import ApiResponseMeta


class ApiErrorDetail(BaseModel):
    """Structured error detail for field or context-level issues."""

    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    field: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class ApiError(BaseModel):
    """Top-level API error envelope."""

    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    details: tuple[ApiErrorDetail, ...] = ()


class ApiErrorResponse(BaseModel):
    """Standard API error response contract."""

    model_config = ConfigDict(frozen=True)

    success: Literal[False] = False
    error: ApiError
    meta: ApiResponseMeta = Field(default_factory=ApiResponseMeta)

