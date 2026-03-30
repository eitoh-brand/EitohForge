"""Health/readiness/status endpoint helpers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from inspect import isawaitable
from time import perf_counter

from fastapi import APIRouter, FastAPI

from eitohforge_sdk.core.config import AppSettings, get_settings


@dataclass(frozen=True)
class HealthCheckResult:
    """Result of an individual subsystem health check."""

    name: str
    healthy: bool
    duration_ms: int
    details: Mapping[str, object] = field(default_factory=dict)
    error: str | None = None


HealthCheckCallable = Callable[[], bool | HealthCheckResult | Awaitable[bool | HealthCheckResult]]


async def run_health_checks(
    checks: Mapping[str, HealthCheckCallable],
) -> tuple[HealthCheckResult, ...]:
    """Run health checks and normalize results."""
    results: list[HealthCheckResult] = []
    for name, check in checks.items():
        started = perf_counter()
        try:
            outcome_or_awaitable = check()
            outcome = await outcome_or_awaitable if isawaitable(outcome_or_awaitable) else outcome_or_awaitable
            elapsed_ms = int((perf_counter() - started) * 1000)
            if isinstance(outcome, HealthCheckResult):
                results.append(
                    HealthCheckResult(
                        name=outcome.name or name,
                        healthy=outcome.healthy,
                        duration_ms=elapsed_ms,
                        details=outcome.details,
                        error=outcome.error,
                    )
                )
            else:
                results.append(HealthCheckResult(name=name, healthy=bool(outcome), duration_ms=elapsed_ms))
        except Exception as exc:
            elapsed_ms = int((perf_counter() - started) * 1000)
            results.append(
                HealthCheckResult(
                    name=name,
                    healthy=False,
                    duration_ms=elapsed_ms,
                    error=str(exc),
                )
            )
    return tuple(results)


def register_health_endpoints(
    app: FastAPI,
    *,
    checks: Mapping[str, HealthCheckCallable] | None = None,
    settings_provider: Callable[[], AppSettings] | None = None,
) -> APIRouter:
    """Register default `/health`, `/ready`, and `/status` endpoints."""
    resolved_checks = checks or {}
    resolved_settings_provider = settings_provider or get_settings
    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/ready")
    async def ready() -> dict[str, object]:
        check_results = await run_health_checks(resolved_checks)
        healthy = all(result.healthy for result in check_results)
        return {
            "status": "ready" if healthy else "not_ready",
            "checks": [result.__dict__ for result in check_results],
        }

    @router.get("/status")
    async def status() -> dict[str, object]:
        settings = resolved_settings_provider()
        check_results = await run_health_checks(resolved_checks)
        healthy = all(result.healthy for result in check_results)
        return {
            "status": "healthy" if healthy else "degraded",
            "service": {"name": settings.app_name, "env": settings.app_env},
            "checks": [result.__dict__ for result in check_results],
            "timestamp": datetime.now(UTC).isoformat(),
        }

    app.include_router(router)
    return router

