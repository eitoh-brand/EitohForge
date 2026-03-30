"""In-memory event bus dispatcher."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable
from dataclasses import dataclass, field

from eitohforge_sdk.infrastructure.messaging.contracts import EventEnvelope, EventHandler


@dataclass
class InMemoryEventBus:
    """In-memory event bus that dispatches to registered handlers."""

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

