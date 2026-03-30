"""Validation context model shared across validation layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ValidationStage(str, Enum):
    """Validation stage boundaries in the application lifecycle."""

    REQUEST = "request"
    DOMAIN = "domain"
    BUSINESS = "business"
    SECURITY = "security"


@dataclass(frozen=True)
class ValidationContext:
    """Execution context for validators."""

    stage: ValidationStage
    actor_id: str | None = None
    tenant_id: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

