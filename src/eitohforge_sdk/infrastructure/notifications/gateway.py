"""In-memory notification gateway baseline."""

from __future__ import annotations

from dataclasses import dataclass, field
from inspect import isawaitable
from uuid import uuid4

from eitohforge_sdk.infrastructure.notifications.contracts import (
    NotificationChannel,
    NotificationGateway,
    NotificationMessage,
    NotificationResult,
    NotificationSender,
)


@dataclass
class InMemoryNotificationGateway(NotificationGateway):
    """In-memory notification gateway for email/sms/push baseline delivery."""

    _senders: dict[NotificationChannel, NotificationSender] = field(default_factory=dict)
    _sent_messages: list[NotificationMessage] = field(default_factory=list)

    @property
    def sent_messages(self) -> tuple[NotificationMessage, ...]:
        return tuple(self._sent_messages)

    def register_sender(self, channel: NotificationChannel, sender: NotificationSender) -> None:
        self._senders[channel] = sender

    async def send(self, message: NotificationMessage) -> NotificationResult:
        sender = self._senders.get(message.channel)
        if sender is None:
            return NotificationResult(
                status="failed",
                channel=message.channel,
                recipient=message.recipient,
                error_message=f"No sender registered for channel: {message.channel}",
            )

        self._sent_messages.append(message)
        try:
            maybe_awaitable = sender(message)
            result = await maybe_awaitable if isawaitable(maybe_awaitable) else maybe_awaitable
            return result
        except Exception as exc:
            return NotificationResult(
                status="failed",
                channel=message.channel,
                recipient=message.recipient,
                error_message=str(exc),
            )

    async def send_many(self, messages: tuple[NotificationMessage, ...]) -> tuple[NotificationResult, ...]:
        results: list[NotificationResult] = []
        for message in messages:
            results.append(await self.send(message))
        return tuple(results)


def success_result_for(message: NotificationMessage) -> NotificationResult:
    """Build a canonical success result for in-memory sender callbacks."""
    return NotificationResult(
        status="sent",
        channel=message.channel,
        recipient=message.recipient,
        provider_message_id=str(uuid4()),
    )

