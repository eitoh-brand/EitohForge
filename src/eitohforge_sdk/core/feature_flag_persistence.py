"""Load feature flag definitions from Redis (JSON blob) for cross-process consistency."""

from __future__ import annotations

import json
from typing import Any

import redis

from eitohforge_sdk.core.feature_flags import FeatureFlagDefinition


def load_definitions_from_redis_json(
    *,
    redis_url: str,
    key: str = "eitohforge:featureflags:definitions",
) -> list[FeatureFlagDefinition]:
    """Fetch a JSON array of flag definitions from Redis and parse into ``FeatureFlagDefinition``.

    Expected payload shape (JSON array):

    ``[{"key": "foo", "enabled": true, "rollout_percentage": 50, ...}, ...]``
    """
    client = redis.Redis.from_url(redis_url, decode_responses=True)
    raw = client.get(key)
    if not raw:
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("Redis feature flag payload must be a JSON array.")
    return [_row_to_definition(row) for row in data]


def _row_to_definition(row: Any) -> FeatureFlagDefinition:
    if not isinstance(row, dict):
        raise ValueError("Each feature flag row must be a JSON object.")
    return FeatureFlagDefinition.from_mapping(row)


def save_definitions_to_redis_json(
    *,
    redis_url: str,
    definitions: list[FeatureFlagDefinition],
    key: str = "eitohforge:featureflags:definitions",
) -> None:
    """Persist definitions as JSON array (for admin tooling or tests)."""
    payload = json.dumps([d.to_mapping() for d in definitions])
    client = redis.Redis.from_url(redis_url, decode_responses=True)
    client.set(key, payload)
