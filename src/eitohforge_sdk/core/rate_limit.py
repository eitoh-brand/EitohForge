"""Rate limiting middleware and in-memory limiter."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response


@dataclass(frozen=True)
class RateLimitRule:
    """Rate limit rule configuration."""

    max_requests: int
    window_seconds: int
    key_headers: tuple[str, ...] = ("x-actor-id", "x-forwarded-for", "x-real-ip")
    scope_path_prefix: str | None = None


class InMemoryRateLimiter:
    """Sliding-window in-memory rate limiter."""

    def __init__(self, now_provider: Callable[[], datetime] | None = None) -> None:
        self._now_provider = now_provider or (lambda: datetime.now(UTC))
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, rule: RateLimitRule) -> tuple[bool, int]:
        now_ts = self._now_provider().timestamp()
        window_start = now_ts - rule.window_seconds
        bucket = self._requests[key]
        while bucket and bucket[0] <= window_start:
            bucket.popleft()

        if len(bucket) >= rule.max_requests:
            retry_after = ceil((bucket[0] + rule.window_seconds) - now_ts)
            return (False, max(1, retry_after))

        bucket.append(now_ts)
        return (True, 0)


def resolve_rate_limit_key(request: Request, headers: tuple[str, ...]) -> str:
    """Resolve a stable request key using configured headers and fallback values."""
    for header in headers:
        value = request.headers.get(header)
        if value:
            return f"{header}:{value.strip().lower()}"
    if request.client is not None and request.client.host:
        return f"client:{request.client.host}"
    return "client:unknown"


def register_rate_limiter_middleware(
    app: FastAPI,
    rule: RateLimitRule,
    *,
    limiter: InMemoryRateLimiter | None = None,
) -> InMemoryRateLimiter:
    """Register request rate-limiting middleware."""
    resolved_limiter = limiter or InMemoryRateLimiter()

    @app.middleware("http")
    async def _rate_limit_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if rule.scope_path_prefix is not None and not request.url.path.startswith(rule.scope_path_prefix):
            return await call_next(request)

        key = resolve_rate_limit_key(request, rule.key_headers)
        allowed, retry_after = resolved_limiter.allow(key, rule)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"success": False, "error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests."}},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(rule.max_requests),
                },
            )
        return await call_next(request)

    return resolved_limiter

