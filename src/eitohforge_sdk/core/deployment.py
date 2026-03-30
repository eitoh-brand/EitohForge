"""Environment profile helpers for dev, staging, and production."""

from __future__ import annotations

from dataclasses import dataclass

from eitohforge_sdk.core.config import AppSettings


@dataclass(frozen=True)
class EnvironmentBehavior:
    """Derived behavior from `AppSettings.app_env` for framework defaults and guardrails."""

    profile: str
    is_local: bool
    is_production_like: bool
    expose_detailed_errors: bool
    recommend_strict_cors: bool
    recommend_rate_limiting: bool


def resolve_environment_behavior(settings: AppSettings) -> EnvironmentBehavior:
    """Map `app_env` to operational expectations (CORS, errors, rate limits)."""
    env = settings.app_env
    is_local = env == "local"
    is_production_like = env in ("staging", "prod")
    expose_detailed_errors = env in ("local", "dev")
    return EnvironmentBehavior(
        profile=env,
        is_local=is_local,
        is_production_like=is_production_like,
        expose_detailed_errors=expose_detailed_errors,
        recommend_strict_cors=is_production_like,
        recommend_rate_limiting=True,
    )
