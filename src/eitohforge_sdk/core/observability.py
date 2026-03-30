"""Observability integration points for metrics, logging, and tracing."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
import logging
from time import perf_counter
from typing import Protocol
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.responses import Response


@dataclass(frozen=True)
class ObservabilityRule:
    """Observability middleware configuration."""

    enabled: bool = True
    enable_metrics: bool = True
    enable_logging: bool = True
    enable_tracing: bool = True
    trace_header: str = "x-trace-id"
    request_id_header: str = "x-request-id"


class MetricsSink(Protocol):
    """Metrics sink abstraction."""

    def increment(self, name: str, value: int = 1, *, tags: Mapping[str, str] | None = None) -> None:
        ...


@dataclass
class InMemoryMetricsSink:
    """In-memory metrics sink for tests/local usage."""

    counters: dict[tuple[str, tuple[tuple[str, str], ...]], int] = field(default_factory=dict)

    def increment(self, name: str, value: int = 1, *, tags: Mapping[str, str] | None = None) -> None:
        tag_tuple = tuple(sorted((tags or {}).items()))
        key = (name, tag_tuple)
        self.counters[key] = self.counters.get(key, 0) + value


def register_observability_middleware(
    app: FastAPI,
    rule: ObservabilityRule,
    *,
    metrics_sink: MetricsSink | None = None,
    logger: logging.Logger | None = None,
) -> MetricsSink:
    """Register request observability middleware."""
    sink = metrics_sink or InMemoryMetricsSink()
    resolved_logger = logger or logging.getLogger("eitohforge.observability")

    @app.middleware("http")
    async def _observability_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not rule.enabled:
            return await call_next(request)

        trace_id = request.headers.get(rule.trace_header) or str(uuid4())
        request_id = request.headers.get(rule.request_id_header) or str(uuid4())
        if rule.enable_tracing:
            request.state.trace_id = trace_id
            request.state.request_id = request_id

        start = perf_counter()
        response = await call_next(request)
        duration_ms = int((perf_counter() - start) * 1000)

        response.headers[rule.trace_header] = trace_id
        response.headers[rule.request_id_header] = request_id

        tags = {
            "method": request.method.upper(),
            "path": request.url.path,
            "status": str(response.status_code),
        }
        if rule.enable_metrics:
            sink.increment("http.requests.total", tags=tags)
            sink.increment("http.requests.duration_ms", value=max(0, duration_ms), tags=tags)
        if rule.enable_logging:
            resolved_logger.info(
                "request.complete",
                extra={
                    "method": tags["method"],
                    "path": tags["path"],
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "trace_id": trace_id,
                    "request_id": request_id,
                },
            )
        return response

    return sink


def get_request_trace_id(request: Request) -> str | None:
    """Read request trace ID from state, when middleware is enabled."""
    return getattr(request.state, "trace_id", None)


def get_request_id(request: Request) -> str | None:
    """Read request ID from state, when middleware is enabled."""
    return getattr(request.state, "request_id", None)

