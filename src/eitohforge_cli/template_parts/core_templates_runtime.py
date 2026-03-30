"""Runtime/middleware core template fragments."""

CORE_RUNTIME_FILE_TEMPLATES: dict[str, str] = {
    "app/core/rate_limit.py": """from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


@dataclass(frozen=True)
class RateLimitRule:
    max_requests: int
    window_seconds: int
    key_headers: tuple[str, ...] = ("x-actor-id", "x-forwarded-for", "x-real-ip")
    scope_path_prefix: str | None = None


class InMemoryRateLimiter:
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
    for header in headers:
        value = request.headers.get(header)
        if value:
            return f"{header}:{value.strip().lower()}"
    if request.client is not None and request.client.host:
        return f"client:{request.client.host}"
    return "client:unknown"


def register_rate_limiter_middleware(
    app: FastAPI, rule: RateLimitRule, *, limiter: InMemoryRateLimiter | None = None
) -> InMemoryRateLimiter:
    resolved_limiter = limiter or InMemoryRateLimiter()

    @app.middleware("http")
    async def _rate_limit_middleware(request: Request, call_next: Callable[..., object]) -> object:
        if rule.scope_path_prefix is not None and not request.url.path.startswith(rule.scope_path_prefix):
            return await call_next(request)

        key = resolve_rate_limit_key(request, rule.key_headers)
        allowed, retry_after = resolved_limiter.allow(key, rule)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests."},
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(rule.max_requests),
                },
            )
        return await call_next(request)

    return resolved_limiter
""",
    "app/core/idempotency.py": """from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
from typing import Protocol

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response


@dataclass(frozen=True)
class IdempotencyRule:
    header_name: str = "idempotency-key"
    write_methods: tuple[str, ...] = ("POST", "PUT", "PATCH", "DELETE")
    ttl_seconds: int = 86400
    max_body_bytes: int = 1048576


@dataclass
class IdempotencyRecord:
    body_hash: str
    status_code: int
    response_body: bytes
    headers: dict[str, str]
    media_type: str | None
    expires_at: datetime


class IdempotencyStore(Protocol):
    def get(self, key: str) -> IdempotencyRecord | None:
        ...

    def put(self, key: str, record: IdempotencyRecord) -> None:
        ...


class InMemoryIdempotencyStore:
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
    app: FastAPI, rule: IdempotencyRule, *, store: IdempotencyStore | None = None
) -> IdempotencyStore:
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
        store_key = f"{request.method.upper()}:{request.url.path}:{request_key.strip()}"
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
                    headers=_sanitize_response_headers(dict(replayable_response.headers)),
                    media_type=replayable_response.media_type,
                    expires_at=datetime.now(UTC) + timedelta(seconds=rule.ttl_seconds),
                ),
            )
        return replayable_response

    return resolved_store


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
""",
    "app/core/request_signing.py": """from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
from typing import Protocol

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response


@dataclass(frozen=True)
class RequestSigningRule:
    enabled: bool = True
    signature_header: str = "x-signature"
    timestamp_header: str = "x-signature-timestamp"
    nonce_header: str = "x-signature-nonce"
    key_id_header: str = "x-signature-key-id"
    allowed_skew_seconds: int = 300
    nonce_ttl_seconds: int = 300
    methods: tuple[str, ...] = ("POST", "PUT", "PATCH", "DELETE")
    scope_path_prefix: str | None = None


@dataclass(frozen=True)
class SignaturePayload:
    method: str
    path: str
    timestamp: str
    nonce: str
    body_sha256_hex: str


class RequestNonceStore(Protocol):
    def mark(self, nonce_key: str, *, expires_at: datetime) -> bool:
        ...


class InMemoryRequestNonceStore:
    def __init__(self, now_provider: Callable[[], datetime] | None = None) -> None:
        self._records: dict[str, datetime] = {}
        self._now_provider = now_provider or (lambda: datetime.now(UTC))

    def mark(self, nonce_key: str, *, expires_at: datetime) -> bool:
        now = self._now_provider()
        self._prune(now)
        if nonce_key in self._records:
            return False
        self._records[nonce_key] = expires_at
        return True

    def _prune(self, now: datetime) -> None:
        for key in tuple(self._records):
            if self._records[key] <= now:
                self._records.pop(key, None)


def compute_request_signature(payload: SignaturePayload, *, secret: str) -> str:
    canonical = (
        f"{payload.method}\\n"
        f"{payload.path}\\n"
        f"{payload.timestamp}\\n"
        f"{payload.nonce}\\n"
        f"{payload.body_sha256_hex}"
    ).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()


def register_request_signing_middleware(
    app: FastAPI,
    rule: RequestSigningRule,
    *,
    resolve_secret: Callable[[str | None], str | None],
    nonce_store: RequestNonceStore | None = None,
    now_provider: Callable[[], datetime] | None = None,
) -> RequestNonceStore:
    resolved_nonce_store = nonce_store or InMemoryRequestNonceStore(now_provider=now_provider)
    resolved_now_provider = now_provider or (lambda: datetime.now(UTC))

    @app.middleware("http")
    async def _request_signing_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not rule.enabled:
            return await call_next(request)
        if request.method.upper() not in {method.upper() for method in rule.methods}:
            return await call_next(request)
        if rule.scope_path_prefix is not None and not request.url.path.startswith(rule.scope_path_prefix):
            return await call_next(request)

        signature = request.headers.get(rule.signature_header)
        timestamp = request.headers.get(rule.timestamp_header)
        nonce = request.headers.get(rule.nonce_header)
        key_id = request.headers.get(rule.key_id_header)
        if not signature or not timestamp or not nonce:
            return _signature_error("MISSING_SIGNATURE_HEADERS", "Missing signature headers.")

        try:
            request_ts = int(timestamp)
        except ValueError:
            return _signature_error("INVALID_SIGNATURE_TIMESTAMP", "Invalid signature timestamp.")

        now = resolved_now_provider()
        if abs(int(now.timestamp()) - request_ts) > rule.allowed_skew_seconds:
            return _signature_error("STALE_SIGNATURE_TIMESTAMP", "Signature timestamp outside allowed skew.")

        nonce_key = f"{key_id or 'default'}:{nonce}"
        if not resolved_nonce_store.mark(
            nonce_key,
            expires_at=now + timedelta(seconds=rule.nonce_ttl_seconds),
        ):
            return _signature_error("REPLAYED_SIGNATURE_NONCE", "Signature nonce has already been used.")

        secret = resolve_secret(key_id)
        if not secret:
            return _signature_error("UNKNOWN_SIGNATURE_KEY", "Unknown request-signing key id.")

        body = await request.body()
        expected = compute_request_signature(
            SignaturePayload(
                method=request.method.upper(),
                path=request.url.path,
                timestamp=timestamp,
                nonce=nonce,
                body_sha256_hex=hashlib.sha256(body).hexdigest(),
            ),
            secret=secret,
        )
        if not hmac.compare_digest(expected, signature):
            return _signature_error("INVALID_REQUEST_SIGNATURE", "Request signature verification failed.")
        return await call_next(request)

    return resolved_nonce_store


def _signature_error(code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"success": False, "error": {"code": code, "message": message}},
    )
""",
    "app/core/capabilities.py": """from collections.abc import Callable

from fastapi import APIRouter, FastAPI

from app.core.config import AppSettings, get_settings


def build_capability_profile(
    settings: AppSettings,
    *,
    api_versions: tuple[str, ...] = ("v1", "v2"),
) -> dict[str, object]:
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "api_versions": api_versions,
        "features": {
            "rate_limit": settings.rate_limit.enabled,
            "idempotency": settings.idempotency.enabled,
            "request_signing": settings.request_signing.enabled,
            "observability": settings.observability.enabled,
            "audit_logging": settings.audit.enabled,
            "analytics_database": settings.database_analytics.enabled,
            "search_database": settings.database_search.enabled,
            "search_integration": settings.search.enabled,
            "tenant_isolation": settings.tenant.enabled,
            "plugin_registry": settings.plugins.enabled,
            "feature_flags": settings.feature_flags.enabled,
            "security_hardening": settings.security_hardening.enabled,
        },
        "providers": {
            "cache": settings.cache.provider,
            "storage": settings.storage.provider,
            "secrets": settings.secrets.provider,
            "search": settings.search.provider,
        },
        "request_signing": {
            "enabled": settings.request_signing.enabled,
            "signature_header": settings.request_signing.signature_header,
            "timestamp_header": settings.request_signing.timestamp_header,
            "nonce_header": settings.request_signing.nonce_header,
            "key_id_header": settings.request_signing.key_id_header,
            "allowed_skew_seconds": settings.request_signing.allowed_skew_seconds,
            "methods": settings.request_signing.methods_tuple,
        },
        "idempotency": {
            "enabled": settings.idempotency.enabled,
            "header_name": settings.idempotency.header_name,
            "write_methods": settings.idempotency.write_methods_tuple,
            "ttl_seconds": settings.idempotency.ttl_seconds,
        },
        "rate_limit": {
            "enabled": settings.rate_limit.enabled,
            "max_requests": settings.rate_limit.max_requests,
            "window_seconds": settings.rate_limit.window_seconds,
            "key_headers": settings.rate_limit.key_headers_tuple,
        },
        "observability": {
            "enabled": settings.observability.enabled,
            "enable_metrics": settings.observability.enable_metrics,
            "enable_logging": settings.observability.enable_logging,
            "enable_tracing": settings.observability.enable_tracing,
            "trace_header": settings.observability.trace_header,
            "request_id_header": settings.observability.request_id_header,
        },
        "audit": {
            "enabled": settings.audit.enabled,
            "methods": settings.audit.methods_tuple,
            "scope_path_prefix": settings.audit.scope_path_prefix,
        },
        "search": {
            "enabled": settings.search.enabled,
            "provider": settings.search.provider,
            "hosts": settings.search.hosts,
            "index_prefix": settings.search.index_prefix,
            "verify_tls": settings.search.verify_tls,
        },
        "tenant": {
            "enabled": settings.tenant.enabled,
            "required_for_write_methods": settings.tenant.required_for_write_methods,
            "write_methods": settings.tenant.write_methods_tuple,
            "scope_path_prefix": settings.tenant.scope_path_prefix,
            "resource_tenant_header": settings.tenant.resource_tenant_header,
        },
        "plugins": {
            "enabled": settings.plugins.enabled,
        },
        "feature_flags": {
            "enabled": settings.feature_flags.enabled,
            "endpoint_path": settings.feature_flags.endpoint_path,
        },
        "security_hardening": {
            "enabled": settings.security_hardening.enabled,
            "max_request_bytes": settings.security_hardening.max_request_bytes,
            "allowed_hosts": settings.security_hardening.allowed_hosts_tuple,
            "add_security_headers": settings.security_hardening.add_security_headers,
        },
    }


def register_capabilities_endpoint(
    app: FastAPI,
    *,
    settings_provider: Callable[[], AppSettings] | None = None,
    api_versions: tuple[str, ...] = ("v1", "v2"),
    path: str = "/sdk/capabilities",
) -> APIRouter:
    router = APIRouter()
    resolved_settings_provider = settings_provider or get_settings

    @router.get(path)
    def sdk_capabilities() -> dict[str, object]:
        return build_capability_profile(resolved_settings_provider(), api_versions=api_versions)

    app.include_router(router)
    return router
""",
    "app/core/health.py": """from datetime import UTC, datetime
from time import perf_counter

from app.core.config import AppSettings, get_settings
from app.infrastructure.cache.factory import build_cache_provider
from app.infrastructure.database.factory import build_database_provider
from app.infrastructure.storage.factory import build_storage_provider


def _database_check(settings: AppSettings) -> tuple[bool, str | None]:
    try:
        return (build_database_provider(settings).ping(), None)
    except Exception as exc:
        return (False, str(exc))


def _cache_check(settings: AppSettings) -> tuple[bool, str | None]:
    try:
        provider = build_cache_provider(settings)
        provider.exists("__health__")
        return (True, None)
    except Exception as exc:
        return (False, str(exc))


def _storage_check(settings: AppSettings) -> tuple[bool, str | None]:
    try:
        provider = build_storage_provider(settings)
        provider.exists("__health__")
        return (True, None)
    except Exception as exc:
        return (False, str(exc))


def _build_checks(settings: AppSettings) -> tuple[dict[str, object], bool]:
    checks: list[dict[str, object]] = []
    for name, check in (
        ("database", _database_check),
        ("cache", _cache_check),
        ("storage", _storage_check),
    ):
        started = perf_counter()
        healthy, error = check(settings)
        checks.append(
            {
                "name": name,
                "healthy": healthy,
                "duration_ms": int((perf_counter() - started) * 1000),
                "error": error,
            }
        )
    overall = all(bool(item["healthy"]) for item in checks)
    return ({"checks": checks}, overall)


def get_readiness_payload(settings: AppSettings | None = None) -> dict[str, object]:
    resolved = settings or get_settings()
    checks_payload, overall = _build_checks(resolved)
    return {"status": "ready" if overall else "not_ready", **checks_payload}


def get_status_payload(settings: AppSettings | None = None) -> dict[str, object]:
    resolved = settings or get_settings()
    checks_payload, overall = _build_checks(resolved)
    return {
        "status": "healthy" if overall else "degraded",
        "service": {"name": resolved.app_name, "env": resolved.app_env},
        "timestamp": datetime.now(UTC).isoformat(),
        **checks_payload,
    }
""",
    "app/core/audit.py": """from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from fastapi import FastAPI, Request
from starlette.responses import Response

from app.core.security_context import get_request_security_context


@dataclass(frozen=True)
class AuditRule:
    enabled: bool = True
    methods: tuple[str, ...] = ("POST", "PUT", "PATCH", "DELETE")
    scope_path_prefix: str | None = None


@dataclass(frozen=True)
class AuditEvent:
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
    def record(self, event: AuditEvent) -> None:
        ...


@dataclass
class InMemoryAuditSink:
    events: list[AuditEvent] = field(default_factory=list)

    def record(self, event: AuditEvent) -> None:
        self.events.append(event)


def log_audit_event(sink: AuditSink, event: AuditEvent) -> None:
    sink.record(event)


def register_audit_middleware(
    app: FastAPI,
    rule: AuditRule,
    *,
    sink: AuditSink | None = None,
) -> AuditSink:
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
""",
    "app/core/observability.py": """from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
import logging
from time import perf_counter
from typing import Protocol
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.responses import Response


@dataclass(frozen=True)
class ObservabilityRule:
    enabled: bool = True
    enable_metrics: bool = True
    enable_logging: bool = True
    enable_tracing: bool = True
    trace_header: str = "x-trace-id"
    request_id_header: str = "x-request-id"


class MetricsSink(Protocol):
    def increment(self, name: str, value: int = 1, *, tags: Mapping[str, str] | None = None) -> None:
        ...


@dataclass
class InMemoryMetricsSink:
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

        tags = {"method": request.method.upper(), "path": request.url.path, "status": str(response.status_code)}
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
    return getattr(request.state, "trace_id", None)


def get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)
""",
    "app/core/tenant.py": """from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from app.core.security_context import (
    SecurityContext,
    build_security_context_from_headers,
    get_request_security_context,
)


_tenant_context_var: ContextVar["TenantContext | None"] = ContextVar(
    "eitohforge_tenant_context",
    default=None,
)


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str | None
    actor_id: str | None
    request_id: str | None
    trace_id: str | None

    @staticmethod
    def current() -> "TenantContext":
        existing = _tenant_context_var.get()
        if isinstance(existing, TenantContext):
            return existing
        return TenantContext(tenant_id=None, actor_id=None, request_id=None, trace_id=None)


@dataclass(frozen=True)
class TenantIsolationRule:
    enabled: bool = True
    required_for_write_methods: bool = True
    write_methods: tuple[str, ...] = ("POST", "PUT", "PATCH", "DELETE")
    scope_path_prefix: str | None = None
    resource_tenant_header: str = "x-resource-tenant-id"


class TenantIsolationError(PermissionError):
    pass


def build_tenant_context_from_security_context(context: SecurityContext) -> TenantContext:
    return TenantContext(
        tenant_id=context.tenant_id,
        actor_id=context.actor_id,
        request_id=context.request_id,
        trace_id=context.trace_id,
    )


def build_tenant_context_from_headers(headers: dict[str, str]) -> TenantContext:
    return build_tenant_context_from_security_context(build_security_context_from_headers(headers))


def get_request_tenant_context(request: Request) -> TenantContext:
    existing = getattr(request.state, "tenant_context", None)
    if isinstance(existing, TenantContext):
        return existing
    context = build_tenant_context_from_security_context(get_request_security_context(request))
    request.state.tenant_context = context
    return context


def assert_tenant_access(tenant_context: TenantContext, *, resource_tenant_id: str | None) -> None:
    if resource_tenant_id is None or not resource_tenant_id.strip():
        return
    if tenant_context.tenant_id is None:
        raise TenantIsolationError("Tenant context is missing for tenant-scoped resource access.")
    if tenant_context.tenant_id != resource_tenant_id.strip():
        raise TenantIsolationError("Cross-tenant access denied.")


def register_tenant_context_middleware(app: FastAPI, rule: TenantIsolationRule) -> None:
    @app.middleware("http")
    async def _tenant_context_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not rule.enabled:
            return await call_next(request)
        if rule.scope_path_prefix is not None and not request.url.path.startswith(rule.scope_path_prefix):
            return await call_next(request)

        tenant_context = build_tenant_context_from_security_context(get_request_security_context(request))
        request.state.tenant_context = tenant_context
        token = _tenant_context_var.set(tenant_context)

        try:
            method = request.method.upper()
            if (
                rule.required_for_write_methods
                and method in set(rule.write_methods)
                and not tenant_context.tenant_id
            ):
                return _tenant_error("TENANT_CONTEXT_REQUIRED", "Tenant context is required for write operations.")

            try:
                assert_tenant_access(
                    tenant_context,
                    resource_tenant_id=request.headers.get(rule.resource_tenant_header),
                )
            except TenantIsolationError:
                return _tenant_error("TENANT_ACCESS_DENIED", "Tenant boundary violation.")

            return await call_next(request)
        finally:
            _tenant_context_var.reset(token)


def _tenant_error(code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=403, content={"success": False, "error": {"code": code, "message": message}})
""",
    "app/core/plugins.py": """from dataclasses import dataclass, field
from typing import Any, Protocol

from fastapi import FastAPI


class PluginModule(Protocol):
    name: str


@dataclass
class PluginRegistry:
    _plugins: dict[str, PluginModule] = field(default_factory=dict)

    def register(self, plugin: PluginModule) -> None:
        key = plugin.name.strip().lower()
        if not key:
            raise ValueError("Plugin name is required.")
        self._plugins[key] = plugin

    def has(self, plugin_name: str) -> bool:
        return plugin_name.strip().lower() in self._plugins

    def list_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._plugins.keys()))

    def apply(
        self,
        *,
        app: FastAPI | None = None,
        provider_registry: dict[str, Any] | None = None,
        event_registry: dict[str, tuple[Any, ...]] | None = None,
    ) -> tuple[str, ...]:
        for plugin in self._plugins.values():
            if app is not None and hasattr(plugin, "register_routes"):
                getattr(plugin, "register_routes")(app)
            if provider_registry is not None and hasattr(plugin, "register_providers"):
                getattr(plugin, "register_providers")(provider_registry)
            if event_registry is not None and hasattr(plugin, "register_events"):
                getattr(plugin, "register_events")(event_registry)
        return self.list_names()
""",
    "app/core/feature_flags.py": """from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib

from fastapi import APIRouter, FastAPI, Request


@dataclass(frozen=True)
class FeatureFlagDefinition:
    key: str
    enabled: bool = True
    rollout_percentage: int = 100
    actor_allowlist: tuple[str, ...] = ()
    tenant_allowlist: tuple[str, ...] = ()
    starts_at: datetime | None = None
    ends_at: datetime | None = None


@dataclass(frozen=True)
class FeatureFlagTargetingContext:
    actor_id: str | None = None
    tenant_id: str | None = None


@dataclass
class FeatureFlagService:
    flags: dict[str, FeatureFlagDefinition] = field(default_factory=dict)
    _now_provider: Callable[[], datetime] = field(default_factory=lambda: (lambda: datetime.now(UTC)))

    def register(self, definition: FeatureFlagDefinition) -> None:
        key = definition.key.strip()
        if not key:
            raise ValueError("Feature flag key is required.")
        self.flags[key] = definition

    def evaluate(self, key: str, *, context: FeatureFlagTargetingContext | None = None) -> bool:
        definition = self.flags.get(key)
        if definition is None or not definition.enabled:
            return False
        now = self._now_provider()
        if definition.starts_at is not None and now < definition.starts_at:
            return False
        if definition.ends_at is not None and now >= definition.ends_at:
            return False
        resolved = context or FeatureFlagTargetingContext()
        if definition.actor_allowlist and resolved.actor_id in set(definition.actor_allowlist):
            return True
        if definition.tenant_allowlist and resolved.tenant_id in set(definition.tenant_allowlist):
            return True
        rollout = max(0, min(100, definition.rollout_percentage))
        if rollout >= 100:
            return True
        if rollout <= 0:
            return False
        subject = resolved.actor_id or resolved.tenant_id or "anonymous"
        bucket = _rollout_bucket(definition.key, subject)
        return bucket < rollout

    def evaluate_many(self, *, context: FeatureFlagTargetingContext | None = None) -> dict[str, bool]:
        return {key: self.evaluate(key, context=context) for key in sorted(self.flags.keys())}


def register_feature_flags_endpoint(
    app: FastAPI,
    *,
    service: FeatureFlagService | None = None,
    path: str = "/sdk/feature-flags",
) -> APIRouter:
    router = APIRouter()
    resolved_service = service or FeatureFlagService()

    @router.get(path)
    def get_feature_flags(request: Request) -> dict[str, object]:
        context = FeatureFlagTargetingContext(
            actor_id=request.headers.get("x-actor-id"),
            tenant_id=request.headers.get("x-tenant-id"),
        )
        return {
            "flags": resolved_service.evaluate_many(context=context),
            "context": {"actor_id": context.actor_id, "tenant_id": context.tenant_id},
        }

    app.include_router(router)
    return router


def _rollout_bucket(flag_key: str, subject: str) -> int:
    digest = hashlib.sha256(f"{flag_key}:{subject}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100
""",
    "app/core/security_hardening.py": """from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response


@dataclass(frozen=True)
class SecurityHardeningRule:
    enabled: bool = True
    max_request_bytes: int = 2_097_152
    allowed_hosts: tuple[str, ...] = ("*",)
    add_security_headers: bool = True
    security_headers: dict[str, str] = field(
        default_factory=lambda: {
            "x-content-type-options": "nosniff",
            "x-frame-options": "DENY",
            "referrer-policy": "no-referrer",
            "x-permitted-cross-domain-policies": "none",
            "content-security-policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        }
    )


def register_security_hardening_middleware(app: FastAPI, rule: SecurityHardeningRule) -> None:
    @app.middleware("http")
    async def _security_hardening_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not rule.enabled:
            return await call_next(request)
        if not _is_host_allowed(request, rule.allowed_hosts):
            return _hardening_error("HOST_NOT_ALLOWED", "Request host is not allowed.")
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > rule.max_request_bytes:
            return _hardening_error("REQUEST_ENTITY_TOO_LARGE", "Request body exceeds allowed size.", status_code=413)
        response = await call_next(request)
        if rule.add_security_headers:
            for key, value in rule.security_headers.items():
                response.headers[key] = value
        return response


def _is_host_allowed(request: Request, allowed_hosts: tuple[str, ...]) -> bool:
    normalized = tuple(host.strip().lower() for host in allowed_hosts if host.strip())
    if not normalized or "*" in normalized:
        return True
    host_header = (request.headers.get("host") or "").split(":")[0].lower().strip()
    return host_header in set(normalized)


def _hardening_error(code: str, message: str, *, status_code: int = 400) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"success": False, "error": {"code": code, "message": message}})
""",
    "app/core/middleware.py": """from fastapi import FastAPI

from app.core.config import get_settings
from app.core.audit import AuditRule, register_audit_middleware
from app.core.error_middleware import register_error_handlers
from app.core.error_registry import build_default_error_registry
from app.core.idempotency import IdempotencyRule, register_idempotency_middleware
from app.core.observability import ObservabilityRule, register_observability_middleware
from app.core.security_hardening import SecurityHardeningRule, register_security_hardening_middleware
from app.core.tenant import TenantIsolationRule, register_tenant_context_middleware
from app.core.rate_limit import RateLimitRule, register_rate_limiter_middleware
from app.core.request_signing import RequestSigningRule, register_request_signing_middleware
from app.core.security_context import register_security_context_middleware


def register_middleware(app: FastAPI) -> None:
    settings = get_settings()
    if settings.security_hardening.enabled:
        register_security_hardening_middleware(
            app,
            SecurityHardeningRule(
                enabled=settings.security_hardening.enabled,
                max_request_bytes=settings.security_hardening.max_request_bytes,
                allowed_hosts=settings.security_hardening.allowed_hosts_tuple,
                add_security_headers=settings.security_hardening.add_security_headers,
            ),
        )
    if settings.audit.enabled:
        register_audit_middleware(
            app,
            AuditRule(
                enabled=settings.audit.enabled,
                methods=settings.audit.methods_tuple,
                scope_path_prefix=settings.audit.scope_path_prefix,
            ),
        )
    if settings.observability.enabled:
        register_observability_middleware(
            app,
            ObservabilityRule(
                enabled=settings.observability.enabled,
                enable_metrics=settings.observability.enable_metrics,
                enable_logging=settings.observability.enable_logging,
                enable_tracing=settings.observability.enable_tracing,
                trace_header=settings.observability.trace_header,
                request_id_header=settings.observability.request_id_header,
            ),
        )
    if settings.request_signing.enabled:
        register_request_signing_middleware(
            app,
            RequestSigningRule(
                enabled=settings.request_signing.enabled,
                signature_header=settings.request_signing.signature_header,
                timestamp_header=settings.request_signing.timestamp_header,
                nonce_header=settings.request_signing.nonce_header,
                key_id_header=settings.request_signing.key_id_header,
                allowed_skew_seconds=settings.request_signing.allowed_skew_seconds,
                nonce_ttl_seconds=settings.request_signing.nonce_ttl_seconds,
                methods=settings.request_signing.methods_tuple,
                scope_path_prefix=settings.request_signing.scope_path_prefix,
            ),
            resolve_secret=lambda key_id: (
                settings.request_signing.shared_secret
                if key_id in (None, "", settings.request_signing.default_key_id)
                else None
            ),
        )
    if settings.idempotency.enabled:
        register_idempotency_middleware(
            app,
            IdempotencyRule(
                header_name=settings.idempotency.header_name,
                write_methods=settings.idempotency.write_methods_tuple,
                ttl_seconds=settings.idempotency.ttl_seconds,
                max_body_bytes=settings.idempotency.max_body_bytes,
            ),
        )
    if settings.rate_limit.enabled:
        register_rate_limiter_middleware(
            app,
            RateLimitRule(
                max_requests=settings.rate_limit.max_requests,
                window_seconds=settings.rate_limit.window_seconds,
                key_headers=settings.rate_limit.key_headers_tuple,
                scope_path_prefix=settings.rate_limit.scope_path_prefix,
            ),
        )
    if settings.tenant.enabled:
        register_tenant_context_middleware(
            app,
            TenantIsolationRule(
                enabled=settings.tenant.enabled,
                required_for_write_methods=settings.tenant.required_for_write_methods,
                write_methods=settings.tenant.write_methods_tuple,
                scope_path_prefix=settings.tenant.scope_path_prefix,
                resource_tenant_header=settings.tenant.resource_tenant_header,
            ),
        )
    register_security_context_middleware(app)
    register_error_handlers(app, build_default_error_registry())
""",
}

