"""Audit logging engine primitives."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from fastapi import FastAPI, Request
from starlette.responses import Response

from eitohforge_sdk.core.security_context import get_request_security_context


@dataclass(frozen=True)
class AuditRule:
    """Audit middleware configuration."""

    enabled: bool = True
    methods: tuple[str, ...] = ("POST", "PUT", "PATCH", "DELETE")
    scope_path_prefix: str | None = None


@dataclass(frozen=True)
class AuditEvent:
    """Audit event payload captured by sink implementations."""

    action: str
    method: str
    path: str
    status_code: int
    actor_id: str | None
    tenant_id: str | None
    request_id: str | None
    trace_id: str | None
    metadata: Mapping[str, str] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class AuditSink(Protocol):
    """Audit sink contract."""

    def record(self, event: AuditEvent) -> None:
        ...


@dataclass
class InMemoryAuditSink:
    """In-memory audit sink for local/testing workflows."""

    events: list[AuditEvent] = field(default_factory=list)

    def record(self, event: AuditEvent) -> None:
        self.events.append(event)


def log_audit_event(sink: AuditSink, event: AuditEvent) -> None:
    """Send an audit event to the configured sink."""
    sink.record(event)


def register_audit_middleware(
    app: FastAPI,
    rule: AuditRule,
    *,
    sink: AuditSink | None = None,
) -> AuditSink:
    """Register request audit middleware and return the resolved sink."""
    resolved_sink = sink or InMemoryAuditSink()

    @app.middleware("http")
    async def _audit_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        if not rule.enabled:
            return response
        if request.method.upper() not in {method.upper() for method in rule.methods}:
            return response
        if rule.scope_path_prefix is not None and not request.url.path.startswith(rule.scope_path_prefix):
            return response

        security_context = get_request_security_context(request)
        log_audit_event(
            resolved_sink,
            AuditEvent(
                action=f"http.{request.method.lower()}",
                method=request.method.upper(),
                path=request.url.path,
                status_code=response.status_code,
                actor_id=security_context.actor_id,
                tenant_id=security_context.tenant_id,
                request_id=security_context.request_id or request.headers.get("x-request-id"),
                trace_id=security_context.trace_id or request.headers.get("x-trace-id"),
                metadata={
                    "client_ip": request.client.host if request.client is not None else "unknown",
                    "user_agent": request.headers.get("user-agent", ""),
                },
            ),
        )
        return response

    return resolved_sink

