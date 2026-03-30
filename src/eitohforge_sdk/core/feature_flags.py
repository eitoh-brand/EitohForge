"""Feature flag service and staged rollout endpoint."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib

from fastapi import APIRouter, FastAPI, Request


@dataclass(frozen=True)
class FeatureFlagDefinition:
    """Feature flag definition with staged rollout controls."""

    key: str
    enabled: bool = True
    rollout_percentage: int = 100
    actor_allowlist: tuple[str, ...] = ()
    tenant_allowlist: tuple[str, ...] = ()
    starts_at: datetime | None = None
    ends_at: datetime | None = None


@dataclass(frozen=True)
class FeatureFlagTargetingContext:
    """Context used to evaluate staged feature flags."""

    actor_id: str | None = None
    tenant_id: str | None = None


@dataclass
class FeatureFlagService:
    """In-memory feature flag evaluator with deterministic rollout bucketing."""

    flags: dict[str, FeatureFlagDefinition] = field(default_factory=dict)
    _now_provider: Callable[[], datetime] = field(default_factory=lambda: (lambda: datetime.now(UTC)))

    def register(self, definition: FeatureFlagDefinition) -> None:
        key = definition.key.strip()
        if not key:
            raise ValueError("Feature flag key is required.")
        self.flags[key] = definition

    def evaluate(
        self, key: str, *, context: FeatureFlagTargetingContext | None = None
    ) -> bool:
        definition = self.flags.get(key)
        if definition is None:
            return False
        if not definition.enabled:
            return False
        now = self._now_provider()
        if definition.starts_at is not None and now < definition.starts_at:
            return False
        if definition.ends_at is not None and now >= definition.ends_at:
            return False

        resolved = context or FeatureFlagTargetingContext()
        if definition.actor_allowlist and resolved.actor_id in set(definition.actor_allowlist):
            return True
        if definition.tenant_allowlist and resolved.tenant_id in set(definition.tenant_allowlist):
            return True

        rollout = max(0, min(100, definition.rollout_percentage))
        if rollout >= 100:
            return True
        if rollout <= 0:
            return False
        subject = resolved.actor_id or resolved.tenant_id or "anonymous"
        bucket = _rollout_bucket(definition.key, subject)
        return bucket < rollout

    def evaluate_many(
        self, *, context: FeatureFlagTargetingContext | None = None
    ) -> dict[str, bool]:
        return {key: self.evaluate(key, context=context) for key in sorted(self.flags.keys())}


def register_feature_flags_endpoint(
    app: FastAPI,
    *,
    service: FeatureFlagService | None = None,
    path: str = "/sdk/feature-flags",
) -> APIRouter:
    """Register feature flag evaluation endpoint."""
    router = APIRouter()

    resolved_service = service or FeatureFlagService()

    @router.get(path)
    def get_feature_flags(request: Request) -> dict[str, object]:
        context = FeatureFlagTargetingContext(
            actor_id=request.headers.get("x-actor-id"),
            tenant_id=request.headers.get("x-tenant-id"),
        )
        return {
            "flags": resolved_service.evaluate_many(context=context),
            "context": {"actor_id": context.actor_id, "tenant_id": context.tenant_id},
        }

    app.include_router(router)
    return router


def _rollout_bucket(flag_key: str, subject: str) -> int:
    digest = hashlib.sha256(f"{flag_key}:{subject}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100
