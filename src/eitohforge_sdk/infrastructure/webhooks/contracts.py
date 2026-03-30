"""Webhook delivery contracts."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class WebhookEvent:
    """Internal webhook event payload."""

    name: str
    payload: Mapping[str, object] = field(default_factory=dict)
    metadata: Mapping[str, str] = field(default_factory=dict)
    event_id: str | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class WebhookEndpointConfig:
    """Webhook endpoint signature/delivery configuration."""

    url: str
    secret: str
    timeout_seconds: float = 5.0
    signature_header: str = "x-webhook-signature"
    timestamp_header: str = "x-webhook-timestamp"
    event_name_header: str = "x-webhook-event"
    event_id_header: str = "x-webhook-event-id"


@dataclass(frozen=True)
class WebhookRequest:
    """Transport-agnostic webhook request envelope."""

    url: str
    body: bytes
    headers: Mapping[str, str]
    timeout_seconds: float = 5.0


@dataclass(frozen=True)
class WebhookResponse:
    """Transport response abstraction for webhook dispatcher."""

    status_code: int
    body: bytes = b""
    headers: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class WebhookDeadLetterRecord:
    """Failed webhook record persisted in dead-letter queue."""

    event: WebhookEvent
    endpoint: WebhookEndpointConfig
    attempts: int
    error_message: str | None = None
    last_status_code: int | None = None


@dataclass(frozen=True)
class WebhookDeliveryResult:
    """Webhook delivery execution result."""

    status: str
    attempts: int
    last_status_code: int | None = None
    error_message: str | None = None


WebhookTransportSend = Callable[[WebhookRequest], Awaitable[WebhookResponse] | WebhookResponse]


class WebhookTransport(Protocol):
    """Transport contract used by webhook dispatcher."""

    def send(self, request: WebhookRequest) -> Awaitable[WebhookResponse] | WebhookResponse:
        ...

