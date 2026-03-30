"""Typed configuration for EitohForge runtime."""

from functools import lru_cache
from typing import Literal
from urllib.parse import quote_plus

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database runtime configuration."""

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
    provider: Literal["memory", "opensearch", "elasticsearch"] = "memory"
    hosts: str = "http://localhost:9200"
    index_prefix: str = "eitohforge"
    username: str | None = None
    password: str | None = None
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


class SecretSettings(BaseSettings):
    """Secret management provider configuration."""

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


class AuthSettings(BaseSettings):
    """Authentication and token settings."""

    model_config = SettingsConfigDict(
        env_prefix="EITOHFORGE_AUTH_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
    jwt_secret: str = Field(default="replace-with-32-plus-char-secret-value", min_length=32)
    access_token_minutes: int = 15
    refresh_token_days: int = 7


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
        return self


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached app settings."""
    return AppSettings()

