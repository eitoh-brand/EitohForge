from __future__ import annotations

import asyncio

from eitohforge_sdk.infrastructure.notifications import (
    InMemoryNotificationGateway,
    NotificationMessage,
    NotificationResult,
    success_result_for,
)


def test_notification_gateway_sends_email_sms_and_push() -> None:
    gateway = InMemoryNotificationGateway()
    gateway.register_sender("email", lambda message: success_result_for(message))
    gateway.register_sender("sms", lambda message: success_result_for(message))
    gateway.register_sender("push", lambda message: success_result_for(message))

    results = asyncio.run(
        gateway.send_many(
            (
                NotificationMessage(channel="email", recipient="a@acme.dev", subject="Hi", body="Hello"),
                NotificationMessage(channel="sms", recipient="+15551234567", body="OTP 1234"),
                NotificationMessage(channel="push", recipient="device-1", body="Ping"),
            )
        )
    )
    assert len(results) == 3
    assert all(result.status == "sent" for result in results)
    assert len(gateway.sent_messages) == 3


def test_notification_gateway_returns_failure_without_sender() -> None:
    gateway = InMemoryNotificationGateway()
    result = asyncio.run(gateway.send(NotificationMessage(channel="email", recipient="a@acme.dev", body="Hello")))
    assert result.status == "failed"
    assert "No sender registered" in (result.error_message or "")


def test_notification_gateway_captures_sender_errors() -> None:
    gateway = InMemoryNotificationGateway()

    def failing_sender(_: NotificationMessage) -> NotificationResult:
        raise RuntimeError("transport unavailable")

    gateway.register_sender("sms", failing_sender)
    result = asyncio.run(gateway.send(NotificationMessage(channel="sms", recipient="+1555000", body="hello")))
    assert result.status == "failed"
    assert result.error_message == "transport unavailable"

