"""Static catalog of SDK feature areas for completeness checks and docs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureArea:
    """One logical capability surface of EitohForge."""

    key: str
    title: str
    module_hint: str
    settings_prefix: str | None


# Single source of truth for "what exists in the SDK" (documentation + tooling).
FORGE_FEATURE_CATALOG: tuple[FeatureArea, ...] = (
    FeatureArea("config", "Typed settings & fail-fast startup", "eitohforge_sdk.core.config", "EITOHFORGE_"),
    FeatureArea("runtime", "CORS, bind hints, public URL", "eitohforge_sdk.core.config", "EITOHFORGE_RUNTIME_"),
    FeatureArea("deployment", "Environment behavior (dev/stage/prod)", "eitohforge_sdk.core.deployment", None),
    FeatureArea(
        "forge_application",
        "build_forge_app wrapper (middleware + platform routes)",
        "eitohforge_sdk.core.forge_application",
        None,
    ),
    FeatureArea("errors", "Error registry + HTTP mapping", "eitohforge_sdk.core.error_registry", None),
    FeatureArea("validation", "Validation engine + hooks", "eitohforge_sdk.core.validation", None),
    FeatureArea("auth_jwt", "JWT access/refresh", "eitohforge_sdk.core.auth.jwt", "EITOHFORGE_AUTH_"),
    FeatureArea("auth_session", "Sessions + Redis store", "eitohforge_sdk.core.auth.session", None),
    FeatureArea("auth_sso", "SSO broker + OIDC/SAML adapters", "eitohforge_sdk.core.auth.sso", None),
    FeatureArea("rbac_abac", "RBAC + ABAC policies", "eitohforge_sdk.core.security", None),
    FeatureArea("tenant", "Tenant context + isolation middleware", "eitohforge_sdk.core.tenant", "EITOHFORGE_TENANT_"),
    FeatureArea("rate_limit", "Rate limiting middleware", "eitohforge_sdk.core.rate_limit", "EITOHFORGE_RATE_LIMIT_"),
    FeatureArea("idempotency", "Idempotency middleware", "eitohforge_sdk.core.idempotency", "EITOHFORGE_IDEMPOTENCY_"),
    FeatureArea("request_signing", "Signed request middleware", "eitohforge_sdk.core.request_signing", None),
    FeatureArea("security_hardening", "Security headers + host/body limits", "eitohforge_sdk.core.security_hardening", None),
    FeatureArea("observability", "Tracing, metrics, logging hooks", "eitohforge_sdk.core.observability", None),
    FeatureArea("audit", "Audit middleware", "eitohforge_sdk.core.audit", None),
    FeatureArea("health", "Health / ready / status", "eitohforge_sdk.core.health", None),
    FeatureArea("capabilities", "Capability profile endpoint", "eitohforge_sdk.core.capabilities", None),
    FeatureArea("feature_flags", "Feature flags + rollout API", "eitohforge_sdk.core.feature_flags", None),
    FeatureArea("api_versioning", "Versioned routers", "eitohforge_sdk.core.api_versioning", None),
    FeatureArea("plugins", "Plugin registry", "eitohforge_sdk.core.plugins", None),
    FeatureArea("database", "DB providers + registry", "eitohforge_sdk.infrastructure.database", "EITOHFORGE_DB_"),
    FeatureArea("cache", "Cache providers + invalidation", "eitohforge_sdk.infrastructure.cache", None),
    FeatureArea("storage", "Storage + S3 + CDN helpers", "eitohforge_sdk.infrastructure.storage", None),
    FeatureArea("search", "Search abstraction + OpenSearch", "eitohforge_sdk.infrastructure.search", None),
    FeatureArea("sockets", "WebSocket JWT + hub", "eitohforge_sdk.infrastructure.sockets", None),
    FeatureArea(
        "realtime_ws_route",
        "Generated /realtime/ws router + JSON protocol",
        "app.presentation.routers.realtime",
        "EITOHFORGE_REALTIME_",
    ),
    FeatureArea("events_jobs", "Event bus + background jobs", "eitohforge_sdk.infrastructure.messaging", None),
    FeatureArea("webhooks", "Webhooks + signing", "eitohforge_sdk.infrastructure.webhooks", None),
    FeatureArea("notifications", "Notification gateway + templates", "eitohforge_sdk.infrastructure.notifications", None),
    FeatureArea("external_api", "Resilient HTTP client", "eitohforge_sdk.infrastructure.external_api", None),
    FeatureArea("transactions_saga", "Saga orchestration scaffold", "eitohforge_sdk.infrastructure.transactions", None),
    FeatureArea("repositories", "SQLAlchemy repository core", "eitohforge_sdk.infrastructure.repositories", None),
)


def list_feature_catalog() -> list[dict[str, str | None]]:
    """Return catalog rows as plain dicts for `/sdk/capabilities` extensions or docs."""
    return [
        {
            "key": area.key,
            "title": area.title,
            "module_hint": area.module_hint,
            "settings_prefix": area.settings_prefix,
        }
        for area in FORGE_FEATURE_CATALOG
    ]
