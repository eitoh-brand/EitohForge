from __future__ import annotations

from eitohforge_sdk.core.forge_application import ForgeAppBuildConfig, build_forge_app
from eitohforge_sdk.core.forge_toggles import (
    ForgePlatformToggles,
    default_forge_platform_toggles,
    effective_feature,
    forge_platform_toggles_uniform,
)


def test_effective_feature_none_uses_setting() -> None:
    assert effective_feature(None, setting_enabled=True) is True
    assert effective_feature(None, setting_enabled=False) is False


def test_effective_feature_explicit_overrides_setting() -> None:
    assert effective_feature(False, setting_enabled=True) is False
    assert effective_feature(True, setting_enabled=False) is True


def test_default_forge_platform_toggles_all_none() -> None:
    t = default_forge_platform_toggles()
    assert all(getattr(t, name) is None for name in ForgePlatformToggles.__dataclass_fields__)


def test_forge_platform_toggles_uniform_all_same() -> None:
    off = forge_platform_toggles_uniform(enabled=False)
    assert all(getattr(off, name) is False for name in ForgePlatformToggles.__dataclass_fields__)
    on = forge_platform_toggles_uniform(enabled=True)
    assert all(getattr(on, name) is True for name in ForgePlatformToggles.__dataclass_fields__)


def test_build_forge_app_uniform_false_skips_platform_routes() -> None:
    app = build_forge_app(
        build=ForgeAppBuildConfig(
            toggles=forge_platform_toggles_uniform(enabled=False),
            wire_realtime_websocket=False,
        )
    )
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/health" not in paths
    assert "/sdk/capabilities" not in paths
