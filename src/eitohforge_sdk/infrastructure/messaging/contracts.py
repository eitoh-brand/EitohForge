"""Internal event bus contracts."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class EventEnvelope:
    """Canonical event payload passed through the internal bus."""

    name: str
    payload: Mapping[str, object] = field(default_factory=dict)
    metadata: Mapping[str, str] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


EventHandler = Callable[[EventEnvelope], Awaitable[None] | None]


class EventBus(Protocol):
    """Internal event dispatcher contract."""

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        ...

    async def publish(self, event: EventEnvelope) -> None:
        ...

