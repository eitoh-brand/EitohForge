"""Feature flag service and staged rollout endpoint."""

from __future__ import annotations

from collections.abc import Callable
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
from typing import Any

from fastapi import APIRouter, FastAPI, Request


@dataclass(frozen=True)
class FeatureFlagDefinition:
    """Feature flag definition with staged rollout controls."""

    key: str
    enabled: bool = True
    rollout_percentage: int = 100
    actor_allowlist: tuple[str, ...] = ()
    tenant_allowlist: tuple[str, ...] = ()
    environment_allowlist: tuple[str, ...] = ()
    cohort_allowlist: tuple[str, ...] = ()
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> FeatureFlagDefinition:
        """Build a definition from JSON-serializable mapping (Redis/DB persistence)."""
        starts_at = _parse_dt(data.get("starts_at"))
        ends_at = _parse_dt(data.get("ends_at"))
        actor_allowlist = data.get("actor_allowlist") or ()
        tenant_allowlist = data.get("tenant_allowlist") or ()
        environment_allowlist = data.get("environment_allowlist") or ()
        cohort_allowlist = data.get("cohort_allowlist") or ()
        if isinstance(actor_allowlist, list):
            actor_allowlist = tuple(str(x) for x in actor_allowlist)
        if isinstance(tenant_allowlist, list):
            tenant_allowlist = tuple(str(x) for x in tenant_allowlist)
        if isinstance(environment_allowlist, list):
            environment_allowlist = tuple(str(x) for x in environment_allowlist)
        if isinstance(cohort_allowlist, list):
            cohort_allowlist = tuple(str(x) for x in cohort_allowlist)
        return cls(
            key=str(data["key"]),
            enabled=bool(data.get("enabled", True)),
            rollout_percentage=int(data.get("rollout_percentage", 100)),
            actor_allowlist=tuple(actor_allowlist),
            tenant_allowlist=tuple(tenant_allowlist),
            environment_allowlist=tuple(environment_allowlist),
            cohort_allowlist=tuple(cohort_allowlist),
            starts_at=starts_at,
            ends_at=ends_at,
        )

    def to_mapping(self) -> dict[str, Any]:
        """Serialize to JSON-friendly dict."""
        return {
            "key": self.key,
            "enabled": self.enabled,
            "rollout_percentage": self.rollout_percentage,
            "actor_allowlist": list(self.actor_allowlist),
            "tenant_allowlist": list(self.tenant_allowlist),
            "environment_allowlist": list(self.environment_allowlist),
            "cohort_allowlist": list(self.cohort_allowlist),
            "starts_at": self.starts_at.isoformat() if self.starts_at else None,
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
        }


def _parse_dt(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None


@dataclass(frozen=True)
class FeatureFlagTargetingContext:
    """Context used to evaluate staged feature flags."""

    actor_id: str | None = None
    tenant_id: str | None = None
    environment: str | None = None
    cohort_id: str | None = None


def targeting_context_from_user(user: object) -> FeatureFlagTargetingContext:
    """Build targeting context from a domain user object (duck-typed)."""
    actor_id = getattr(user, "actor_id", None)
    if actor_id is None:
        uid = getattr(user, "id", None)
        actor_id = str(uid) if uid is not None else None
    elif not isinstance(actor_id, str):
        actor_id = str(actor_id)
    tenant_raw = getattr(user, "tenant_id", None)
    tenant_id = str(tenant_raw) if tenant_raw is not None else None
    env_raw = getattr(user, "environment", None)
    environment = str(env_raw).strip() if env_raw is not None else None
    cohort_raw = getattr(user, "cohort_id", None)
    cohort_id = str(cohort_raw) if cohort_raw is not None else None
    return FeatureFlagTargetingContext(
        actor_id=actor_id,
        tenant_id=tenant_id,
        environment=environment,
        cohort_id=cohort_id,
    )


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

    def reload(self, definitions: Iterable[FeatureFlagDefinition]) -> None:
        """Replace all definitions (used after loading from Redis/DB)."""
        self.flags.clear()
        for definition in definitions:
            self.register(definition)

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

        if definition.environment_allowlist:
            envs = set(definition.environment_allowlist)
            if resolved.environment is None or resolved.environment not in envs:
                return False
        if definition.cohort_allowlist:
            cohorts = set(definition.cohort_allowlist)
            if resolved.cohort_id is None or resolved.cohort_id not in cohorts:
                return False

        rollout = max(0, min(100, definition.rollout_percentage))
        if rollout >= 100:
            return True
        if rollout <= 0:
            return False
        subject = resolved.actor_id or resolved.tenant_id or "anonymous"
        bucket = _rollout_bucket(definition.key, subject)
        return bucket < rollout

    def enabled(
        self, key: str, *, context: FeatureFlagTargetingContext | None = None
    ) -> bool:
        """Alias for :meth:`evaluate` (NestJS-style naming)."""
        return self.evaluate(key, context=context)

    def evaluate_for_user(self, key: str, user: object | None) -> bool:
        """Evaluate using :func:`targeting_context_from_user` when ``user`` is not ``None``."""
        if user is None:
            return self.evaluate(key, context=None)
        return self.evaluate(key, context=targeting_context_from_user(user))

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
            environment=request.headers.get("x-environment"),
            cohort_id=request.headers.get("x-cohort-id"),
        )
        return {
            "flags": resolved_service.evaluate_many(context=context),
            "context": {
                "actor_id": context.actor_id,
                "tenant_id": context.tenant_id,
                "environment": context.environment,
                "cohort_id": context.cohort_id,
            },
        }

    app.include_router(router)
    return router


def _rollout_bucket(flag_key: str, subject: str) -> int:
    digest = hashlib.sha256(f"{flag_key}:{subject}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100
