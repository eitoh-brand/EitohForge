"""Per-request build overrides for `build_forge_app` (tri-state: None = use AppSettings)."""

from __future__ import annotations

from dataclasses import dataclass


def effective_feature(toggle: bool | None, *, setting_enabled: bool) -> bool:
    """Resolve a platform feature: explicit toggle wins; otherwise use settings."""
    return setting_enabled if toggle is None else toggle


@dataclass(frozen=True)
class ForgePlatformToggles:
    """Optional overrides for each platform layer. `None` = follow `AppSettings.*.enabled` (or equivalent).

    Use this to force features on/off regardless of environment, or combine with env-driven settings.
    """

    security_hardening: bool | None = None
    audit: bool | None = None
    observability: bool | None = None
    request_signing: bool | None = None
    idempotency: bool | None = None
    rate_limit: bool | None = None
    tenant: bool | None = None
    security_context: bool | None = None
    cors: bool | None = None
    health: bool | None = None
    capabilities: bool | None = None
    feature_flags: bool | None = None
    realtime_websocket: bool | None = None
    https_redirect: bool | None = None
    api_contract: bool | None = None


def default_forge_platform_toggles() -> ForgePlatformToggles:
    """All `None` — every layer follows `AppSettings` and runtime flags."""
    return ForgePlatformToggles()


def forge_platform_toggles_uniform(*, enabled: bool) -> ForgePlatformToggles:
    """Set every platform toggle to the same value (overrides `AppSettings` for each layer).

    Use ``enabled=False`` for a quick “all middleware and built-in routes controlled by
    toggles are off” baseline; combine with ``ForgeAppBuildConfig(wire_*=...)`` if you also
    want to skip router families regardless of toggle resolution.
    """
    return ForgePlatformToggles(
        security_hardening=enabled,
        audit=enabled,
        observability=enabled,
        request_signing=enabled,
        idempotency=enabled,
        rate_limit=enabled,
        tenant=enabled,
        security_context=enabled,
        cors=enabled,
        health=enabled,
        capabilities=enabled,
        feature_flags=enabled,
        realtime_websocket=enabled,
        https_redirect=enabled,
        api_contract=enabled,
    )
