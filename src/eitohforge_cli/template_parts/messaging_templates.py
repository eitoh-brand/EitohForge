"""Messaging infrastructure template fragments."""

MESSAGING_FILE_TEMPLATES: dict[str, str] = {
    "app/infrastructure/messaging/__init__.py": """from app.infrastructure.messaging.contracts import EventBus, EventEnvelope, EventHandler
from app.infrastructure.messaging.dispatcher import InMemoryEventBus
""",
    "app/infrastructure/messaging/contracts.py": """from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class EventEnvelope:
    name: str
    payload: Mapping[str, object] = field(default_factory=dict)
    metadata: Mapping[str, str] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


EventHandler = Callable[[EventEnvelope], Awaitable[None] | None]


class EventBus(Protocol):
    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        ...

    async def publish(self, event: EventEnvelope) -> None:
        ...
""",
    "app/infrastructure/messaging/dispatcher.py": """from collections import defaultdict
from collections.abc import Awaitable
from dataclasses import dataclass, field

from app.infrastructure.messaging.contracts import EventEnvelope, EventHandler


@dataclass
class InMemoryEventBus:
    _handlers: dict[str, list[EventHandler]] = field(default_factory=lambda: defaultdict(list))
    _wildcard_event_name: str = "*"

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._handlers[event_name].append(handler)

    async def publish(self, event: EventEnvelope) -> None:
        for handler in self._resolve_handlers(event.name):
            maybe_awaitable = handler(event)
            if isinstance(maybe_awaitable, Awaitable):
                await maybe_awaitable

    async def publish_many(self, events: tuple[EventEnvelope, ...]) -> None:
        for event in events:
            await self.publish(event)

    def _resolve_handlers(self, event_name: str) -> tuple[EventHandler, ...]:
        specific = self._handlers.get(event_name, [])
        wildcard = self._handlers.get(self._wildcard_event_name, [])
        return tuple(specific) + tuple(wildcard)
""",
}

