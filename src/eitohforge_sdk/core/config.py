"""Typed configuration for EitohForge runtime."""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database runtime configuration.

    For **Postgres**, ``name`` is the database name and ``driver`` defaults to ``postgresql+psycopg``.

    For **MySQL**, use ``driver`` such as ``mysql+pymysql``, set ``port`` (commonly ``3306``), and
    ``name`` to the schema/database name. Raw connections use ``pymysql``.

    For **SQLite**, set ``driver`` to ``sqlite`` or ``sqlite+pysqlite``; ``name`` is the database path
    (relative or absolute), or ``:memory:`` for an in-memory database. Host, port, username, and
    password are ignored for SQLite.
    """

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
    name: str = "eitohforge"

    @property
    def sqlalchemy_url(self) -> str:
        """Return SQLAlchemy-compatible connection URL."""
        driver_lower = self.driver.lower()
        if driver_lower.startswith("sqlite"):
            db = self.name.strip()
            if db == ":memory:":
                return "sqlite+pysqlite:///:memory:"
            path = Path(db).expanduser()
            resolved = path.resolve()
            return f"sqlite+pysqlite:///{resolved.as_posix()}"
        user = quote_plus(self.username)
        password = quote_plus(self.password)
        return f"{self.driver}://{user}:{password}@{self.host}:{self.port}/{self.name}"


class AnalyticsDatabaseSettings(DatabaseSettings):
    """Analytics database configuration."""

    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_DB_ANALYTICS_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    enabled: bool = False
    name: str = "eitohforge_analytics"


class SearchDatabaseSettings(DatabaseSettings):
    """Search database configuration."""

    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_DB_SEARCH_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    enabled: bool = False
    name: str = "eitohforge_search"


class CacheSettings(BaseSettings):
    """Cache runtime configuration."""

    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_CACHE_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    provider: Literal["redis", "memory", "memcached"] = "redis"
    redis_url: str = "redis://localhost:6379/0"
    default_ttl_seconds: int = Field(default=60, ge=1)


class RateLimitSettings(BaseSettings):
    """Rate-limiting runtime configuration."""

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
    """Idempotency middleware runtime configuration."""

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
    """Request signing middleware runtime configuration."""

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
    """Observability runtime configuration."""

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
    enable_prometheus: bool = False
    prometheus_metrics_path: str = "/metrics"
    otel_enabled: bool = False
    otel_service_name: str = "eitohforge"
    # OTLP traces over HTTP endpoint, e.g. `http://localhost:4318/v1/traces`.
    # If unset while `otel_enabled=true`, tracing falls back to a console exporter.
    otel_otlp_http_endpoint: str | None = None


class AuditSettings(BaseSettings):
    """Audit logging runtime configuration."""

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
    """Search engine provider configuration."""

    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_SEARCH_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    enabled: bool = False
    provider: Literal["memory", "opensearch", "elasticsearch", "meilisearch"] = "memory"
    hosts: str = "http://localhost:9200"
    index_prefix: str = "eitohforge"
    username: str | None = None
    password: str | None = None
    api_key: str | None = None
    verify_tls: bool = True


class TenantSettings(BaseSettings):
    """Tenant isolation settings."""

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
    # Optional per-tenant schema isolation for SQL databases (Postgres).
    # When enabled, SQLAlchemy repositories attempt to set `search_path` at the
    # start of each session scope, using the resolved tenant id.
    db_schema_isolation_enabled: bool = False
    db_schema_name_template: str = "{tenant_id}"

    @field_validator("db_schema_name_template")
    @classmethod
    def _validate_schema_name_template(cls, v: str) -> str:
        if "{tenant_id}" not in v:
            raise ValueError('db_schema_name_template must include "{tenant_id}".')
        return v

    @property
    def write_methods_tuple(self) -> tuple[str, ...]:
        return tuple(part.strip().upper() for part in self.write_methods.split(",") if part.strip())


class PluginSettings(BaseSettings):
    """Plugin registry settings."""

    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_PLUGIN_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    enabled: bool = True


class FeatureFlagSettings(BaseSettings):
    """Feature flag service settings."""

    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_FEATURE_FLAGS_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    enabled: bool = True
    endpoint_path: str = "/sdk/feature-flags"


class SecurityHardeningSettings(BaseSettings):
    """HTTP security hardening settings."""

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
    """Storage runtime configuration."""

    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_STORAGE_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    provider: Literal["local", "s3", "azure", "minio", "gcs"] = "local"
    bucket_name: str = "eitohforge-local-bucket"
    region: str = "us-east-1"
    endpoint_url: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None
    presign_expires_seconds: int = Field(default=900, ge=1, le=604800)
    public_base_url: str | None = None
    cdn_base_url: str | None = None
    azure_connection_string: str | None = None
    gcs_project_id: str | None = None


class SecretSettings(BaseSettings):
    """Secret management provider configuration."""

    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_SECRET_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    provider: Literal["env", "vault", "aws", "azure", "gcp"] = "env"
    vault_url: str | None = None
    vault_mount: str = "secret"
    aws_region: str | None = None
    azure_vault_url: str | None = None
    gcp_project_id: str | None = None


class AuthSettings(BaseSettings):
    """Authentication and token settings."""

    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_AUTH_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    jwt_enabled: bool = True
    jwt_secret: str = Field(default="replace-with-32-plus-char-secret-value", min_length=32)
    access_token_minutes: int = 15
    refresh_token_days: int = 7


class RuntimeSettings(BaseSettings):
    """HTTP runtime: CORS, public URL, and default bind hints for dev/prod."""

    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_RUNTIME_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    public_base_url: str | None = None
    cors_allow_origins: str = ""
    cors_allow_credentials: bool = False
    trust_forwarded_headers: bool = False
    enforce_https_redirect: bool = False
    default_bind_host: str = "127.0.0.1"
    default_bind_port: int = Field(default=8000, ge=1, le=65535)

    @property
    def cors_origins_tuple(self) -> tuple[str, ...]:
        return tuple(part.strip() for part in self.cors_allow_origins.split(",") if part.strip())


class RealtimeSettings(BaseSettings):
    """WebSocket realtime (JWT handshake, rooms; in-memory hub by default)."""

    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_REALTIME_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    enabled: bool = True
    require_access_jwt: bool = True
    redis_url: str | None = None
    redis_broadcast_channel: str = "eitohforge:realtime:broadcast"

    @field_validator("redis_url", mode="before")
    @classmethod
    def _normalize_redis_url(cls, v: object) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s or None
        return None


class ApiVersioningSettings(BaseSettings):
    """HTTP API version lifecycle (deprecation headers on ``/v1`` routes)."""

    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_API_VERSION_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    deprecate_v1: bool = False
    v1_sunset_http_date: str | None = None
    v1_link_deprecation: str | None = None


class ApiContractSettings(BaseSettings):
    """Enforce unified JSON response envelopes on successful routes (optional)."""

    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_API_CONTRACT_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    enforce_json_envelope: bool = False


class AppSettings(BaseSettings):
    """Top-level app settings."""

    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    app_name: str = "eitohforge-service"
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
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)
    realtime: RealtimeSettings = Field(default_factory=RealtimeSettings)
    api_versioning: ApiVersioningSettings = Field(default_factory=ApiVersioningSettings)
    api_contract: ApiContractSettings = Field(default_factory=ApiContractSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    secrets: SecretSettings = Field(default_factory=SecretSettings)

    @model_validator(mode="after")
    def validate_startup_constraints(self) -> "AppSettings":
        """Validate cross-setting startup constraints."""
        if self.app_env != "local" and self.auth.jwt_secret.startswith("replace-with-"):
            raise ValueError(
                "EITOHFORGE_AUTH_JWT_SECRET must be explicitly set outside local environment."
            )
        if self.request_signing.enabled and self.request_signing.shared_secret.startswith("replace-with-"):
            raise ValueError(
                "EITOHFORGE_REQUEST_SIGNING_SHARED_SECRET must be set when request signing is enabled."
            )
        if self.app_env == "prod" and any(o.strip() == "*" for o in self.runtime.cors_origins_tuple):
            raise ValueError(
                "Wildcard CORS (EITOHFORGE_RUNTIME_CORS_ALLOW_ORIGINS=*) is not allowed when EITOHFORGE_APP_ENV=prod."
            )
        if self.realtime.enabled and self.realtime.require_access_jwt and not self.auth.jwt_enabled:
            raise ValueError(
                "Realtime WebSocket requires JWT when EITOHFORGE_REALTIME_REQUIRE_ACCESS_JWT=true "
                "but EITOHFORGE_AUTH_JWT_ENABLED=false."
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached app settings."""
    return AppSettings()

