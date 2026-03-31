"""Notification gateway contracts."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal, Protocol

NotificationChannel = Literal["email", "sms", "push", "whatsapp"]


@dataclass(frozen=True)
class NotificationMessage:
    """Normalized notification message payload."""

    channel: NotificationChannel
    recipient: str
    subject: str | None = None
    body: str = ""
    template_id: str | None = None
    template_vars: Mapping[str, object] = field(default_factory=dict)
    metadata: Mapping[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class NotificationResult:
    """Notification delivery outcome."""

    status: str
    channel: NotificationChannel
    recipient: str
    provider_message_id: str | None = None
    error_message: str | None = None


NotificationSender = Callable[[NotificationMessage], Awaitable[NotificationResult] | NotificationResult]


class NotificationGateway(Protocol):
    """Notification gateway abstraction for email/sms/push."""

    def register_sender(self, channel: NotificationChannel, sender: NotificationSender) -> None:
        ...

    async def send(self, message: NotificationMessage) -> NotificationResult:
        ...

    async def send_many(self, messages: tuple[NotificationMessage, ...]) -> tuple[NotificationResult, ...]:
        ...

