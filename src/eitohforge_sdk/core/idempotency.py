"""Idempotency middleware for write operations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
from typing import Protocol

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response


@dataclass(frozen=True)
class IdempotencyRule:
    """Idempotency middleware configuration."""

    header_name: str = "idempotency-key"
    write_methods: tuple[str, ...] = ("POST", "PUT", "PATCH", "DELETE")
    ttl_seconds: int = 86_400
    max_body_bytes: int = 1_048_576


@dataclass
class IdempotencyRecord:
    """Persisted idempotency response record."""

    body_hash: str
    status_code: int
    response_body: bytes
    headers: dict[str, str]
    media_type: str | None
    expires_at: datetime


class IdempotencyStore(Protocol):
    """Idempotency storage contract."""

    def get(self, key: str) -> IdempotencyRecord | None:
        ...

    def put(self, key: str, record: IdempotencyRecord) -> None:
        ...


class InMemoryIdempotencyStore:
    """In-memory idempotency store."""

    def __init__(self, now_provider: Callable[[], datetime] | None = None) -> None:
        self._records: dict[str, IdempotencyRecord] = {}
        self._now_provider = now_provider or (lambda: datetime.now(UTC))

    def get(self, key: str) -> IdempotencyRecord | None:
        record = self._records.get(key)
        if record is None:
            return None
        if record.expires_at <= self._now_provider():
            self._records.pop(key, None)
            return None
        return record

    def put(self, key: str, record: IdempotencyRecord) -> None:
        self._records[key] = record


def register_idempotency_middleware(
    app: FastAPI,
    rule: IdempotencyRule,
    *,
    store: IdempotencyStore | None = None,
) -> IdempotencyStore:
    """Register idempotency middleware for write requests."""
    resolved_store = store or InMemoryIdempotencyStore()

    @app.middleware("http")
    async def _idempotency_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method.upper() not in {method.upper() for method in rule.write_methods}:
            return await call_next(request)

        request_key = request.headers.get(rule.header_name)
        if request_key is None or not request_key.strip():
            return await call_next(request)

        body = await request.body()
        body_hash = hashlib.sha256(body).hexdigest()
        store_key = _build_store_key(request, request_key)
        existing = resolved_store.get(store_key)

        if existing is not None:
            if existing.body_hash != body_hash:
                return JSONResponse(
                    status_code=409,
                    content={
                        "success": False,
                        "error": {
                            "code": "IDEMPOTENCY_KEY_REUSED",
                            "message": "Idempotency key reused with different request payload.",
                        },
                    },
                )
            headers = dict(existing.headers)
            headers["X-Idempotent-Replay"] = "true"
            return Response(
                content=existing.response_body,
                status_code=existing.status_code,
                media_type=existing.media_type,
                headers=headers,
            )

        response = await call_next(request)
        replayable_response, response_body = await _extract_response_body(response)
        if replayable_response.status_code < 500 and len(response_body) <= rule.max_body_bytes:
            resolved_store.put(
                store_key,
                IdempotencyRecord(
                    body_hash=body_hash,
                    status_code=replayable_response.status_code,
                    response_body=response_body,
                    headers=_sanitize_response_headers(dict(replayable_response.headers.items())),
                    media_type=replayable_response.media_type,
                    expires_at=datetime.now(UTC) + timedelta(seconds=rule.ttl_seconds),
                ),
            )
        return replayable_response

    return resolved_store


def _build_store_key(request: Request, request_key: str) -> str:
    return f"{request.method.upper()}:{request.url.path}:{request_key.strip()}"


async def _extract_response_body(response: Response) -> tuple[Response, bytes]:
    body_attr = getattr(response, "body", None)
    if isinstance(body_attr, bytes):
        return (response, body_attr)

    body = b""
    if hasattr(response, "body_iterator"):
        async for chunk in response.body_iterator:
            body += chunk
    replayable = Response(
        content=body,
        status_code=response.status_code,
        media_type=response.media_type,
        headers=dict(response.headers),
        background=response.background,
    )
    return (replayable, body)


def _sanitize_response_headers(headers: dict[str, str]) -> dict[str, str]:
    ignored = {"content-length", "date", "server", "transfer-encoding"}
    return {key: value for key, value in headers.items() if key.lower() not in ignored}

