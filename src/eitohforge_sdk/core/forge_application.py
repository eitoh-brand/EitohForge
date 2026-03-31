"""Opinionated FastAPI assembly for EitohForge apps (middleware + platform routes)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
import inspect
from typing import Any

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

from eitohforge_sdk.core.api_contract_middleware import ApiContractRule, register_api_contract_middleware
from eitohforge_sdk.core.api_version_deprecation import register_api_version_deprecation_middleware
from eitohforge_sdk.core.audit import AuditRule, register_audit_middleware
from eitohforge_sdk.core.capabilities import register_capabilities_endpoint
from eitohforge_sdk.core.config import AppSettings, get_settings
from eitohforge_sdk.core.error_middleware import register_error_handlers
from eitohforge_sdk.core.error_registry import ErrorRegistry, build_default_error_registry
from eitohforge_sdk.core.feature_flags import FeatureFlagService, register_feature_flags_endpoint
from eitohforge_sdk.core.forge_toggles import ForgePlatformToggles, effective_feature
from eitohforge_sdk.core.health import register_health_endpoints
from eitohforge_sdk.core.idempotency import IdempotencyRule, register_idempotency_middleware
from eitohforge_sdk.core.observability import (
    ObservabilityRule,
    PrometheusMetricsSink,
    register_observability_middleware,
    register_prometheus_metrics_endpoint,
)
from eitohforge_sdk.core.rate_limit import RateLimitRule, register_rate_limiter_middleware
from eitohforge_sdk.core.request_signing import RequestSigningRule, register_request_signing_middleware
from eitohforge_sdk.core.security_context import register_security_context_middleware
from eitohforge_sdk.core.security_hardening import SecurityHardeningRule, register_security_hardening_middleware
from eitohforge_sdk.core.tenant import TenantIsolationRule, register_tenant_context_middleware
from eitohforge_sdk.infrastructure.sockets.realtime_redis import run_realtime_redis_subscriber
from eitohforge_sdk.infrastructure.sockets.realtime_router import attach_socket_hub, build_realtime_router


@dataclass(frozen=True)
class ForgeAppBuildConfig:
    """Controls how `build_forge_app` wires SDK middleware and built-in routes.

    Use `toggles` for per-field overrides (`True`/`False`); `None` means follow `AppSettings`.
    Existing `wire_*` flags still apply on top (e.g. `wire_health_family=False` skips health entirely).
    """

    title: str | None = None
    wire_platform_middleware: bool = True
    wire_health_family: bool = True
    wire_capabilities: bool = True
    wire_feature_flags: bool = True
    wire_realtime_websocket: bool = True
    feature_flag_service: FeatureFlagService | None = None
    error_registry: ErrorRegistry | None = None
    settings_provider: Callable[[], AppSettings] | None = None
    toggles: ForgePlatformToggles | None = None


def build_forge_app(*, build: ForgeAppBuildConfig) -> FastAPI:
    """Create a FastAPI app with standard EitohForge middleware and optional platform routes."""
    settings_provider = build.settings_provider or get_settings
    settings = settings_provider()
    t = build.toggles

    def on(field: str, setting_enabled: bool) -> bool:
        toggle = getattr(t, field) if t is not None else None
        return effective_feature(toggle, setting_enabled=setting_enabled)

    wire_rt = (
        build.wire_platform_middleware
        and build.wire_realtime_websocket
        and on("realtime_websocket", settings.realtime.enabled)
        and settings.realtime.enabled
    )
    redis_rt_url = settings.realtime.redis_url if wire_rt else None

    @asynccontextmanager
    async def _realtime_redis_lifespan(app: FastAPI) -> AsyncIterator[None]:
        stop = asyncio.Event()
        task = asyncio.create_task(
            run_realtime_redis_subscriber(app, settings_provider=settings_provider, stop=stop)
        )
        try:
            yield
        finally:
            stop.set()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            hub: Any = getattr(app.state, "socket_hub", None)
            aclose = getattr(hub, "aclose", None) if hub is not None else None
            if callable(aclose):
                try:
                    result = aclose()
                    if inspect.isawaitable(result):
                        await result
                except Exception:
                    pass

    app = FastAPI(
        title=build.title if build.title is not None else settings.app_name,
        lifespan=_realtime_redis_lifespan if redis_rt_url else None,
    )
    register_api_version_deprecation_middleware(app, settings_provider=settings_provider)

    if not build.wire_platform_middleware:
        if on("https_redirect", settings.runtime.enforce_https_redirect):
            app.add_middleware(HTTPSRedirectMiddleware)
        _attach_cors(app, settings, t)
        return app

    if on("https_redirect", settings.runtime.enforce_https_redirect):
        app.add_middleware(HTTPSRedirectMiddleware)

    if on("security_hardening", settings.security_hardening.enabled):
        register_security_hardening_middleware(
            app,
            SecurityHardeningRule(
                enabled=True,
                max_request_bytes=settings.security_hardening.max_request_bytes,
                allowed_hosts=settings.security_hardening.allowed_hosts_tuple,
                add_security_headers=settings.security_hardening.add_security_headers,
            ),
        )
    if on("audit", settings.audit.enabled):
        register_audit_middleware(
            app,
            AuditRule(
                enabled=True,
                methods=settings.audit.methods_tuple,
                scope_path_prefix=settings.audit.scope_path_prefix,
            ),
        )
    if on("observability", settings.observability.enabled):
        metrics_sink: PrometheusMetricsSink | None = None
        if settings.observability.enable_prometheus:
            metrics_sink = PrometheusMetricsSink(namespace="eitohforge")
            register_prometheus_metrics_endpoint(
                app,
                metrics_sink=metrics_sink,
                path=settings.observability.prometheus_metrics_path,
            )

        otel_tracer: object | None = None
        if settings.observability.otel_enabled and settings.observability.enable_tracing:
            try:
                from opentelemetry import trace
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                from opentelemetry.sdk.resources import Resource
                from opentelemetry.sdk.trace import TracerProvider
                from opentelemetry.sdk.trace.export import (
                    BatchSpanProcessor,
                    ConsoleSpanExporter,
                    SimpleSpanProcessor,
                )

                resource = Resource.create(
                    {"service.name": settings.observability.otel_service_name or settings.app_name}
                )
                provider = TracerProvider(resource=resource)
                exporter: Any
                if settings.observability.otel_otlp_http_endpoint:
                    exporter = OTLPSpanExporter(endpoint=settings.observability.otel_otlp_http_endpoint)
                    provider.add_span_processor(BatchSpanProcessor(exporter))
                else:
                    # Console exporter is best-effort for dev/tests; use synchronous processor
                    # to avoid shutdown-time export warnings.
                    exporter = ConsoleSpanExporter()
                    provider.add_span_processor(SimpleSpanProcessor(exporter))
                trace.set_tracer_provider(provider)
                otel_tracer = trace.get_tracer(settings.observability.otel_service_name or settings.app_name)
            except Exception:
                # Observability must not fail app startup.
                otel_tracer = None

        register_observability_middleware(
            app,
            ObservabilityRule(
                enabled=True,
                enable_metrics=settings.observability.enable_metrics,
                enable_logging=settings.observability.enable_logging,
                enable_tracing=settings.observability.enable_tracing,
                trace_header=settings.observability.trace_header,
                request_id_header=settings.observability.request_id_header,
            ),
            metrics_sink=metrics_sink,
            otel_tracer=otel_tracer,
        )
    if on("request_signing", settings.request_signing.enabled):
        register_request_signing_middleware(
            app,
            RequestSigningRule(
                enabled=True,
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
    if on("idempotency", settings.idempotency.enabled):
        register_idempotency_middleware(
            app,
            IdempotencyRule(
                header_name=settings.idempotency.header_name,
                write_methods=settings.idempotency.write_methods_tuple,
                ttl_seconds=settings.idempotency.ttl_seconds,
                max_body_bytes=settings.idempotency.max_body_bytes,
            ),
        )
    if on("rate_limit", settings.rate_limit.enabled):
        register_rate_limiter_middleware(
            app,
            RateLimitRule(
                max_requests=settings.rate_limit.max_requests,
                window_seconds=settings.rate_limit.window_seconds,
                key_headers=settings.rate_limit.key_headers_tuple,
                scope_path_prefix=settings.rate_limit.scope_path_prefix,
            ),
        )
    if on("tenant", settings.tenant.enabled):
        register_tenant_context_middleware(
            app,
            TenantIsolationRule(
                enabled=True,
                required_for_write_methods=settings.tenant.required_for_write_methods,
                write_methods=settings.tenant.write_methods_tuple,
                scope_path_prefix=settings.tenant.scope_path_prefix,
                resource_tenant_header=settings.tenant.resource_tenant_header,
            ),
        )
    if on("security_context", True):
        register_security_context_middleware(app)
    register_error_handlers(app, build.error_registry or build_default_error_registry())
    if on("api_contract", settings.api_contract.enforce_json_envelope):
        register_api_contract_middleware(
            app,
            rule=ApiContractRule(enabled=True),
        )

    if build.wire_health_family and on("health", True):
        register_health_endpoints(app, settings_provider=settings_provider)
    if build.wire_capabilities and on("capabilities", True):
        register_capabilities_endpoint(app, settings_provider=settings_provider)
    if (
        build.wire_feature_flags
        and on("feature_flags", settings.feature_flags.enabled)
        and settings.feature_flags.enabled
    ):
        register_feature_flags_endpoint(
            app,
            service=build.feature_flag_service or FeatureFlagService(),
            path=settings.feature_flags.endpoint_path,
        )

    if build.wire_realtime_websocket and on("realtime_websocket", settings.realtime.enabled):
        attach_socket_hub(app, settings_provider=settings_provider)
        app.include_router(build_realtime_router(settings_provider=settings_provider))

    _attach_cors(app, settings, t)
    return app


def _attach_cors(app: FastAPI, settings: AppSettings, t: ForgePlatformToggles | None) -> None:
    origins = list(settings.runtime.cors_origins_tuple)
    cors_on = effective_feature(getattr(t, "cors", None) if t is not None else None, setting_enabled=bool(origins))
    if not cors_on or not origins:
        return
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=settings.runtime.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
