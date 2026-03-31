"""Configuration helper commands."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import typer

config_app = typer.Typer(help="Configuration and environment profile helpers.")

_ENV_GROUPS: tuple[tuple[str, str], ...] = (
    ("EITOHFORGE_APP_", "App identity and env posture"),
    ("EITOHFORGE_RUNTIME_", "Runtime/CORS/public URL defaults"),
    ("EITOHFORGE_DB_", "Primary SQL database connection"),
    ("EITOHFORGE_DB_ANALYTICS_", "Analytics database connection"),
    ("EITOHFORGE_DB_SEARCH_", "Search datastore connection"),
    ("EITOHFORGE_AUTH_", "JWT/session/SSO auth behavior"),
    ("EITOHFORGE_RATE_LIMIT_", "Rate limiting controls"),
    ("EITOHFORGE_IDEMPOTENCY_", "Idempotency middleware behavior"),
    ("EITOHFORGE_REQUEST_SIGNING_", "HMAC request-signing controls"),
    ("EITOHFORGE_TENANT_", "Tenant isolation controls"),
    ("EITOHFORGE_FEATURE_FLAGS_", "Feature flags endpoint settings"),
    ("EITOHFORGE_REALTIME_", "WebSocket/realtime settings"),
    ("EITOHFORGE_OBSERVABILITY_", "Tracing/metrics/logging/Prometheus"),
    ("EITOHFORGE_AUDIT_", "Audit middleware settings"),
    ("EITOHFORGE_STORAGE_", "Blob/object storage provider"),
    ("EITOHFORGE_CACHE_", "Cache provider settings"),
    ("EITOHFORGE_SECRET_", "Secret provider selection"),
)

_PROFILE_TEMPLATES: dict[str, tuple[str, ...]] = {
    "local": (
        "EITOHFORGE_APP_ENV=local",
        "EITOHFORGE_DB_DRIVER=sqlite",
        "EITOHFORGE_DB_NAME=:memory:",
        "EITOHFORGE_REALTIME_ENABLED=false",
        "EITOHFORGE_OBSERVABILITY_ENABLED=true",
    ),
    "dev": (
        "EITOHFORGE_APP_ENV=dev",
        "EITOHFORGE_DB_DRIVER=postgresql+psycopg",
        "EITOHFORGE_RATE_LIMIT_ENABLED=false",
        "EITOHFORGE_REQUEST_SIGNING_ENABLED=false",
        "EITOHFORGE_OBSERVABILITY_ENABLED=true",
    ),
    "staging": (
        "EITOHFORGE_APP_ENV=staging",
        "EITOHFORGE_DB_DRIVER=postgresql+psycopg",
        "EITOHFORGE_REALTIME_ENABLED=true",
        "EITOHFORGE_RATE_LIMIT_ENABLED=true",
        "EITOHFORGE_REQUEST_SIGNING_ENABLED=true",
    ),
    "prod": (
        "EITOHFORGE_APP_ENV=prod",
        "EITOHFORGE_RUNTIME_ENFORCE_HTTPS_REDIRECT=true",
        "EITOHFORGE_SECURITY_HARDENING_ENABLED=true",
        "EITOHFORGE_RATE_LIMIT_ENABLED=true",
        "EITOHFORGE_REQUEST_SIGNING_ENABLED=true",
    ),
}

_FEATURE_FLAGS: dict[str, str] = {
    "security_hardening": "EITOHFORGE_SECURITY_HARDENING_ENABLED",
    "audit": "EITOHFORGE_AUDIT_ENABLED",
    "observability": "EITOHFORGE_OBSERVABILITY_ENABLED",
    "request_signing": "EITOHFORGE_REQUEST_SIGNING_ENABLED",
    "idempotency": "EITOHFORGE_IDEMPOTENCY_ENABLED",
    "rate_limit": "EITOHFORGE_RATE_LIMIT_ENABLED",
    "tenant": "EITOHFORGE_TENANT_ENABLED",
    "feature_flags": "EITOHFORGE_FEATURE_FLAGS_ENABLED",
    "realtime": "EITOHFORGE_REALTIME_ENABLED",
    "jwt": "EITOHFORGE_AUTH_JWT_ENABLED",
    "https_redirect": "EITOHFORGE_RUNTIME_ENFORCE_HTTPS_REDIRECT",
    "realtime_jwt": "EITOHFORGE_REALTIME_REQUIRE_ACCESS_JWT",
    "multi_db_analytics": "EITOHFORGE_DB_ANALYTICS_ENABLED",
    "multi_db_search": "EITOHFORGE_DB_SEARCH_ENABLED",
}


def _set_env_value(env_file: Path, key: str, value: str) -> None:
    lines: list[str] = []
    if env_file.exists():
        lines = env_file.read_text(encoding="utf-8").splitlines()
    updated = False
    new_lines: list[str] = []
    prefix = f"{key}="
    for line in lines:
        if line.startswith(prefix):
            new_lines.append(f"{key}={value}")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        new_lines.append(f"{key}={value}")
    env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


@config_app.command("env-groups")
def env_groups() -> None:
    """List supported EITOHFORGE_* env variable groups."""
    for prefix, description in _ENV_GROUPS:
        typer.echo(f"{prefix:<30} {description}")


@config_app.command("env-template")
def env_template(
    profile: Literal["local", "dev", "staging", "prod"] = typer.Option(
        "local", "--profile", help="Environment posture template to print."
    ),
) -> None:
    """Print a starter environment template for the selected profile."""
    typer.echo(f"# EitohForge environment template ({profile})")
    for line in _PROFILE_TEMPLATES[profile]:
        typer.echo(line)


@config_app.command("feature-list")
def feature_list() -> None:
    """List CLI-managed runtime feature flags."""
    for name, env_var in _FEATURE_FLAGS.items():
        typer.echo(f"{name:<20} {env_var}")


@config_app.command("feature-set")
def feature_set(
    feature: Literal[
        "security_hardening",
        "audit",
        "observability",
        "request_signing",
        "idempotency",
        "rate_limit",
        "tenant",
        "feature_flags",
        "realtime",
        "jwt",
        "https_redirect",
        "realtime_jwt",
        "multi_db_analytics",
        "multi_db_search",
    ] = typer.Argument(..., help="Feature key to toggle."),
    enabled: Literal["true", "false"] = typer.Option(
        ..., "--enabled", help="Target value: true|false."
    ),
    env_file: Path = typer.Option(Path(".env"), "--env-file", help="Env file to edit."),
) -> None:
    """Enable/disable a feature by writing the corresponding EITOHFORGE_* flag."""
    env_var = _FEATURE_FLAGS[feature]
    resolved = env_file.resolve()
    _set_env_value(resolved, env_var, enabled)
    typer.echo(f"Updated {resolved}: {env_var}={enabled}")
