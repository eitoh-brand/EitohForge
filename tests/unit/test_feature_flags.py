from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from eitohforge_sdk.core.feature_flags import (
    FeatureFlagDefinition,
    FeatureFlagService,
    FeatureFlagTargetingContext,
    register_feature_flags_endpoint,
    targeting_context_from_user,
)


def test_feature_flag_service_supports_allowlist_and_rollout() -> None:
    service = FeatureFlagService()
    service.register(
        FeatureFlagDefinition(
            key="new-dashboard",
            enabled=True,
            rollout_percentage=0,
            actor_allowlist=("actor-1",),
        )
    )
    assert service.evaluate("new-dashboard", context=FeatureFlagTargetingContext(actor_id="actor-1")) is True
    assert service.evaluate("new-dashboard", context=FeatureFlagTargetingContext(actor_id="actor-2")) is False


def test_feature_flag_service_respects_active_window() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    service = FeatureFlagService(_now_provider=lambda: now)
    service.register(
        FeatureFlagDefinition(
            key="time-boxed-flag",
            starts_at=now + timedelta(minutes=1),
            ends_at=now + timedelta(minutes=2),
        )
    )
    assert service.evaluate("time-boxed-flag") is False


def test_feature_flag_environment_and_cohort_gates() -> None:
    service = FeatureFlagService()
    service.register(
        FeatureFlagDefinition(
            key="env-only",
            enabled=True,
            rollout_percentage=100,
            environment_allowlist=("prod",),
        )
    )
    assert service.evaluate("env-only", context=FeatureFlagTargetingContext(environment="prod")) is True
    assert service.evaluate("env-only", context=FeatureFlagTargetingContext(environment="dev")) is False

    service.register(
        FeatureFlagDefinition(
            key="cohort-only",
            enabled=True,
            rollout_percentage=100,
            cohort_allowlist=("beta",),
        )
    )
    assert service.evaluate("cohort-only", context=FeatureFlagTargetingContext(cohort_id="beta")) is True
    assert service.evaluate("cohort-only", context=FeatureFlagTargetingContext(cohort_id="ga")) is False


def test_feature_flag_enabled_alias_and_evaluate_for_user() -> None:
    service = FeatureFlagService()
    service.register(FeatureFlagDefinition(key="u", enabled=True, rollout_percentage=100))

    class _U:
        id = "user-1"
        tenant_id = "t1"
        environment = "prod"
        cohort_id = "beta"

    assert service.enabled("u", context=FeatureFlagTargetingContext(actor_id="actor-1")) is True
    assert service.evaluate_for_user("u", _U()) is True
    assert service.evaluate_for_user("u", None) is True

    ctx = targeting_context_from_user(_U())
    assert ctx.actor_id == "user-1"
    assert ctx.tenant_id == "t1"
    assert ctx.environment == "prod"
    assert ctx.cohort_id == "beta"


def test_feature_flags_endpoint_returns_evaluations() -> None:
    app = FastAPI()
    service = FeatureFlagService()
    service.register(FeatureFlagDefinition(key="beta-feature", rollout_percentage=100))
    register_feature_flags_endpoint(app, service=service)

    client = TestClient(app)
    response = client.get(
        "/sdk/feature-flags",
        headers={
            "x-actor-id": "actor-1",
            "x-tenant-id": "tenant-a",
            "x-environment": "prod",
            "x-cohort-id": "beta",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["flags"]["beta-feature"] is True
    assert payload["context"]["actor_id"] == "actor-1"
    assert payload["context"]["tenant_id"] == "tenant-a"
    assert payload["context"]["environment"] == "prod"
    assert payload["context"]["cohort_id"] == "beta"
