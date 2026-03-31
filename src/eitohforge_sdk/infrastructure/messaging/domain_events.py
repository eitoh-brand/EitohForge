"""Typed domain events mapped to :class:`EventEnvelope` for the internal event bus."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from eitohforge_sdk.infrastructure.messaging.contracts import EventBus, EventEnvelope


class DomainEvent(BaseModel):
    """Immutable domain event with a logical ``name`` and optional aggregate id."""

    model_config = ConfigDict(frozen=True)

    name: str
    aggregate_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, str] = Field(default_factory=dict)

    def to_envelope(self) -> EventEnvelope:
        """Project into the generic bus envelope."""
        meta = dict(self.metadata)
        if self.aggregate_id is not None:
            meta.setdefault("aggregate_id", self.aggregate_id)
        return EventEnvelope(name=self.name, payload=self.payload, metadata=meta)


class DomainEventPublisher:
    """Publishes :class:`DomainEvent` instances through an :class:`EventBus`."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    async def publish(self, event: DomainEvent) -> None:
        await self._bus.publish(event.to_envelope())

    async def publish_payload(
        self,
        name: str,
        payload: Mapping[str, Any],
        *,
        aggregate_id: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> None:
        """Convenience for ad-hoc events without constructing a subclass."""
        await self.publish(
            DomainEvent(
                name=name,
                aggregate_id=aggregate_id,
                payload=dict(payload),
                metadata=dict(metadata or {}),
            )
        )
