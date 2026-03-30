"""FastAPI exception middleware/handlers backed by an error registry."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from eitohforge_sdk.application.dto.error import ApiError, ApiErrorDetail, ApiErrorResponse
from eitohforge_sdk.application.dto.response import ApiResponseMeta
from eitohforge_sdk.core.error_registry import ErrorRegistry, build_default_error_registry
from eitohforge_sdk.core.validation.errors import ValidationFailedError


def register_error_handlers(app: FastAPI, registry: ErrorRegistry | None = None) -> ErrorRegistry:
    """Register global exception handlers using the provided error registry."""
    resolved_registry = registry or build_default_error_registry()

    @app.exception_handler(Exception)
    async def _handle_exception(request: Request, exc: Exception) -> JSONResponse:
        definition = resolved_registry.resolve(exc)
        details = _extract_details(exc)
        message = str(exc) or definition.default_message
        error = ApiError(code=definition.code, message=message, details=details)
        meta = ApiResponseMeta(
            request_id=request.headers.get("x-request-id"),
            trace_id=request.headers.get("x-trace-id"),
        )
        payload = ApiErrorResponse(error=error, meta=meta)
        return JSONResponse(status_code=definition.status_code, content=payload.model_dump(mode="json"))

    return resolved_registry


def _extract_details(exc: Exception) -> tuple[ApiErrorDetail, ...]:
    if isinstance(exc, ValidationFailedError):
        return tuple(
            ApiErrorDetail(
                code=issue.code,
                message=issue.message,
                field=issue.field,
                context={"severity": issue.severity.value},
            )
            for issue in exc.result.issues
        )
    return ()

