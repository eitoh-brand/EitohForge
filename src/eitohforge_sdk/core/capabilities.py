"""Capability profile endpoint helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import APIRouter, FastAPI

from eitohforge_sdk.core.config import AppSettings, get_settings


@dataclass(frozen=True)
class CapabilityFeatureFlags:
    """Feature toggle snapshot for SDK consumers."""

    rate_limit: bool
    idempotency: bool
    request_signing: bool
    observability: bool
    audit_logging: bool
    analytics_database: bool
    search_database: bool
    search_integration: bool
    tenant_isolation: bool
    plugin_registry: bool
    feature_flags: bool
    security_hardening: bool


def build_capability_profile(
    settings: AppSettings,
    *,
    api_versions: tuple[str, ...] = ("v1", "v2"),
) -> dict[str, object]:
    """Build a mobile/client-consumable capability profile payload."""
    features = CapabilityFeatureFlags(
        rate_limit=settings.rate_limit.enabled,
        idempotency=settings.idempotency.enabled,
        request_signing=settings.request_signing.enabled,
        observability=settings.observability.enabled,
        audit_logging=settings.audit.enabled,
        analytics_database=settings.database_analytics.enabled,
        search_database=settings.database_search.enabled,
        search_integration=settings.search.enabled,
        tenant_isolation=settings.tenant.enabled,
        plugin_registry=settings.plugins.enabled,
        feature_flags=settings.feature_flags.enabled,
        security_hardening=settings.security_hardening.enabled,
    )
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "api_versions": api_versions,
        "features": {
            "rate_limit": features.rate_limit,
            "idempotency": features.idempotency,
            "request_signing": features.request_signing,
            "observability": features.observability,
            "audit_logging": features.audit_logging,
            "analytics_database": features.analytics_database,
            "search_database": features.search_database,
            "search_integration": features.search_integration,
            "tenant_isolation": features.tenant_isolation,
            "plugin_registry": features.plugin_registry,
            "feature_flags": features.feature_flags,
            "security_hardening": features.security_hardening,
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
    """Register a read-only capability profile endpoint."""
    router = APIRouter()
    resolved_settings_provider = settings_provider or get_settings

    @router.get(path)
    def sdk_capabilities() -> dict[str, object]:
        return build_capability_profile(resolved_settings_provider(), api_versions=api_versions)

    app.include_router(router)
    return router

