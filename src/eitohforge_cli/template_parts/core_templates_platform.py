"""Platform and bootstrap core template fragments."""

CORE_PLATFORM_FILE_TEMPLATES: dict[str, str] = {
    'app/core/versioning.py': """from enum import Enum

from fastapi import APIRouter, FastAPI


class ApiVersion(str, Enum):
    V1 = "v1"
    V2 = "v2"


def build_versioned_router(version: ApiVersion, *routers: APIRouter) -> APIRouter:
    root = APIRouter(prefix=f"/{version.value}")
    for router in routers:
        root.include_router(router)
    return root


def register_versioned_routers(app: FastAPI, version_routers: dict[ApiVersion, tuple[APIRouter, ...]]) -> None:
    for version, routers in version_routers.items():
        app.include_router(build_versioned_router(version, *routers))
""",
    'app/core/__init__.py': """from app.core.abac import TenantMatchPolicy, abac_required, require_policies
from app.core.audit import AuditEvent, AuditRule, InMemoryAuditSink, register_audit_middleware
from app.core.auth import JwtTokenManager, OidcSsoProvider, SamlSsoProvider, SessionManager, SsoBroker, TokenType
from app.core.capabilities import build_capability_profile, register_capabilities_endpoint
from app.core.feature_flags import FeatureFlagService, register_feature_flags_endpoint
from app.core.error_middleware import register_error_handlers
from app.core.error_registry import ErrorDefinition, ErrorRegistry, build_default_error_registry
from app.core.health import get_readiness_payload, get_status_payload
from app.core.idempotency import IdempotencyRule, InMemoryIdempotencyStore, register_idempotency_middleware
from app.core.observability import (
    InMemoryMetricsSink,
    ObservabilityRule,
    get_request_id,
    get_request_trace_id,
    register_observability_middleware,
)
from app.core.rate_limit import InMemoryRateLimiter, RateLimitRule, register_rate_limiter_middleware
from app.core.request_signing import (
    InMemoryRequestNonceStore,
    RequestSigningRule,
    SignaturePayload,
    compute_request_signature,
    register_request_signing_middleware,
)
from app.core.security import SecurityPrincipal, rbac_required, require_roles
from app.core.security_context import SecurityContext, get_request_security_context
from app.core.tenant import TenantContext, TenantIsolationRule, register_tenant_context_middleware
from app.core.plugins import PluginRegistry
from app.core.security_hardening import SecurityHardeningRule, register_security_hardening_middleware
from app.core.versioning import ApiVersion, register_versioned_routers
""",
    'app/core/config.py': """from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_DB_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    driver: str = "postgresql+psycopg"
    host: str = "localhost"
    port: int = 5432
    username: str = "postgres"
    password: str = "postgres"
    name: str = "{{ package_name }}"

    @property
    def sqlalchemy_url(self) -> str:
        from urllib.parse import quote_plus

        user = quote_plus(self.username)
        password = quote_plus(self.password)
        return f"{self.driver}://{user}:{password}@{self.host}:{self.port}/{self.name}"


class AnalyticsDatabaseSettings(DatabaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_DB_ANALYTICS_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    enabled: bool = False
    name: str = "{{ package_name }}_analytics"


class SearchDatabaseSettings(DatabaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_DB_SEARCH_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    enabled: bool = False
    name: str = "{{ package_name }}_search"


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_AUTH_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    jwt_secret: str = Field(default="replace-with-32-plus-char-secret-value", min_length=32)
    access_token_minutes: int = 15
    refresh_token_days: int = 7


class CacheSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_CACHE_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    provider: Literal["redis", "memory", "memcached"] = "redis"
    redis_url: str = "redis://localhost:6379/0"
    default_ttl_seconds: int = Field(default=60, ge=1)


class RateLimitSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_RATE_LIMIT_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    enabled: bool = True
    max_requests: int = Field(default=120, ge=1)
    window_seconds: int = Field(default=60, ge=1)
    key_headers: str = "x-actor-id,x-forwarded-for,x-real-ip"
    scope_path_prefix: str | None = None

    @property
    def key_headers_tuple(self) -> tuple[str, ...]:
        return tuple(part.strip().lower() for part in self.key_headers.split(",") if part.strip())


class IdempotencySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_IDEMPOTENCY_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    enabled: bool = True
    header_name: str = "idempotency-key"
    ttl_seconds: int = Field(default=86400, ge=1)
    write_methods: str = "POST,PUT,PATCH,DELETE"
    max_body_bytes: int = Field(default=1048576, ge=1)

    @property
    def write_methods_tuple(self) -> tuple[str, ...]:
        return tuple(part.strip().upper() for part in self.write_methods.split(",") if part.strip())


class RequestSigningSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_REQUEST_SIGNING_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    enabled: bool = False
    shared_secret: str = "replace-with-request-signing-secret"
    signature_header: str = "x-signature"
    timestamp_header: str = "x-signature-timestamp"
    nonce_header: str = "x-signature-nonce"
    key_id_header: str = "x-signature-key-id"
    default_key_id: str = "default"
    allowed_skew_seconds: int = Field(default=300, ge=1)
    nonce_ttl_seconds: int = Field(default=300, ge=1)
    methods: str = "POST,PUT,PATCH,DELETE"
    scope_path_prefix: str | None = None

    @property
    def methods_tuple(self) -> tuple[str, ...]:
        return tuple(part.strip().upper() for part in self.methods.split(",") if part.strip())


class ObservabilitySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_OBSERVABILITY_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    enabled: bool = True
    enable_metrics: bool = True
    enable_logging: bool = True
    enable_tracing: bool = True
    trace_header: str = "x-trace-id"
    request_id_header: str = "x-request-id"


class AuditSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_AUDIT_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    enabled: bool = True
    methods: str = "POST,PUT,PATCH,DELETE"
    scope_path_prefix: str | None = None

    @property
    def methods_tuple(self) -> tuple[str, ...]:
        return tuple(part.strip().upper() for part in self.methods.split(",") if part.strip())


class SearchSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_SEARCH_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    enabled: bool = False
    provider: Literal["memory", "opensearch", "elasticsearch"] = "memory"
    hosts: str = "http://localhost:9200"
    index_prefix: str = "eitohforge"
    username: str | None = None
    password: str | None = None
    verify_tls: bool = True


class TenantSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_TENANT_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    enabled: bool = True
    required_for_write_methods: bool = True
    write_methods: str = "POST,PUT,PATCH,DELETE"
    scope_path_prefix: str | None = None
    resource_tenant_header: str = "x-resource-tenant-id"

    @property
    def write_methods_tuple(self) -> tuple[str, ...]:
        return tuple(part.strip().upper() for part in self.write_methods.split(",") if part.strip())


class PluginSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_PLUGIN_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    enabled: bool = True


class FeatureFlagSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_FEATURE_FLAGS_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    enabled: bool = True
    endpoint_path: str = "/sdk/feature-flags"


class SecurityHardeningSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_SECURITY_HARDENING_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    enabled: bool = True
    max_request_bytes: int = Field(default=2_097_152, ge=1024)
    allowed_hosts: str = "*"
    add_security_headers: bool = True

    @property
    def allowed_hosts_tuple(self) -> tuple[str, ...]:
        return tuple(part.strip() for part in self.allowed_hosts.split(",") if part.strip())


class StorageSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_STORAGE_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    provider: Literal["local", "s3", "azure", "minio", "gcs"] = "local"
    bucket_name: str = "{{ package_name }}-local-bucket"
    region: str = "us-east-1"
    endpoint_url: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None
    presign_expires_seconds: int = Field(default=900, ge=1, le=604800)
    public_base_url: str | None = None
    cdn_base_url: str | None = None


class SecretSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_SECRET_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    provider: Literal["env", "vault", "aws", "azure"] = "env"
    vault_url: str | None = None
    vault_mount: str = "secret"
    aws_region: str | None = None
    azure_vault_url: str | None = None


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    app_name: str = "{{ project_name }}"
    app_env: Literal["local", "dev", "staging", "prod"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    database_analytics: AnalyticsDatabaseSettings = Field(default_factory=AnalyticsDatabaseSettings)
    database_search: SearchDatabaseSettings = Field(default_factory=SearchDatabaseSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    idempotency: IdempotencySettings = Field(default_factory=IdempotencySettings)
    request_signing: RequestSigningSettings = Field(default_factory=RequestSigningSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    audit: AuditSettings = Field(default_factory=AuditSettings)
    search: SearchSettings = Field(default_factory=SearchSettings)
    tenant: TenantSettings = Field(default_factory=TenantSettings)
    plugins: PluginSettings = Field(default_factory=PluginSettings)
    feature_flags: FeatureFlagSettings = Field(default_factory=FeatureFlagSettings)
    security_hardening: SecurityHardeningSettings = Field(default_factory=SecurityHardeningSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    secrets: SecretSettings = Field(default_factory=SecretSettings)

    @model_validator(mode="after")
    def validate_startup_constraints(self) -> "AppSettings":
        if self.app_env != "local" and self.auth.jwt_secret.startswith("replace-with-"):
            raise ValueError(
                "EITOHFORGE_AUTH_JWT_SECRET must be explicitly set outside local environment."
            )
        if self.request_signing.enabled and self.request_signing.shared_secret.startswith("replace-with-"):
            raise ValueError(
                "EITOHFORGE_REQUEST_SIGNING_SHARED_SECRET must be set when request signing is enabled."
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()
""",
    'app/core/secrets.py': """from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from app.core.config import AppSettings


class SecretNotFoundError(KeyError):
    pass


class SecretProvider(Protocol):
    def get(self, key: str) -> str | None:
        ...


def require_secret(provider: SecretProvider, key: str) -> str:
    value = provider.get(key)
    if value is None:
        raise SecretNotFoundError(f"Missing required secret: {key}")
    return value


@dataclass
class EnvSecretProvider:
    def get(self, key: str) -> str | None:
        return os.environ.get(key)


@dataclass
class UnconfiguredSecretProvider:
    provider_name: str

    def get(self, key: str) -> str | None:
        raise NotImplementedError(
            f"Secret provider '{self.provider_name}' is not implemented yet for key: {key}"
        )


def build_secret_provider(settings: AppSettings) -> SecretProvider:
    if settings.secrets.provider == "env":
        return EnvSecretProvider()
    return UnconfiguredSecretProvider(provider_name=settings.secrets.provider)
""",
    'app/core/dependencies.py': """# Shared dependency providers live here.
""",
    'app/core/error_registry.py': """from dataclasses import dataclass

from app.core.validation.errors import ValidationFailedError
from app.domain.value_objects.errors import DomainInvariantError


@dataclass(frozen=True)
class ErrorDefinition:
    code: str
    status_code: int
    default_message: str


class ErrorRegistry:
    def __init__(self) -> None:
        self._definitions: dict[type[BaseException], ErrorDefinition] = {}

    def register(self, exception_type: type[BaseException], definition: ErrorDefinition) -> None:
        self._definitions[exception_type] = definition

    def resolve(self, error: BaseException) -> ErrorDefinition:
        for candidate in type(error).mro():
            if candidate in self._definitions:
                return self._definitions[candidate]
        return ErrorDefinition(
            code="INTERNAL_SERVER_ERROR",
            status_code=500,
            default_message="An unexpected internal error occurred.",
        )


def build_default_error_registry() -> ErrorRegistry:
    registry = ErrorRegistry()
    registry.register(
        ValidationFailedError,
        ErrorDefinition(
            code="VALIDATION_FAILED",
            status_code=422,
            default_message="Request or business validation failed.",
        ),
    )
    registry.register(
        DomainInvariantError,
        ErrorDefinition(
            code="DOMAIN_INVARIANT_VIOLATION",
            status_code=422,
            default_message="Domain invariant validation failed.",
        ),
    )
    registry.register(
        PermissionError,
        ErrorDefinition(
            code="PERMISSION_DENIED",
            status_code=403,
            default_message="Permission denied.",
        ),
    )
    registry.register(
        KeyError,
        ErrorDefinition(
            code="RESOURCE_NOT_FOUND",
            status_code=404,
            default_message="Requested resource was not found.",
        ),
    )
    return registry
""",
    'app/core/error_middleware.py': """from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.application.dto.error import ApiError, ApiErrorDetail, ApiErrorResponse
from app.application.dto.response import ApiResponseMeta
from app.core.error_registry import ErrorRegistry, build_default_error_registry
from app.core.validation.errors import ValidationFailedError


def register_error_handlers(app: FastAPI, registry: ErrorRegistry | None = None) -> ErrorRegistry:
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
""",
    'app/core/middleware.py': """from fastapi import FastAPI

from app.core.error_middleware import register_error_handlers
from app.core.error_registry import build_default_error_registry
from app.core.security_context import register_security_context_middleware


def register_middleware(app: FastAPI) -> None:
    register_security_context_middleware(app)
    register_error_handlers(app, build_default_error_registry())
""",
    'app/core/lifecycle.py': """from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _ = app
    yield
""",
}
