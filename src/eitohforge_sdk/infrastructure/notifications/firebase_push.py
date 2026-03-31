"""Firebase Cloud Messaging push sender (optional ``firebase-admin``)."""

from __future__ import annotations

import importlib
from typing import Any

from eitohforge_sdk.infrastructure.notifications.contracts import (
    NotificationMessage,
    NotificationResult,
    NotificationSender,
)


def _messaging_module() -> Any:
    try:
        return importlib.import_module("firebase_admin.messaging")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Firebase push requires 'firebase-admin'. "
            "Install via `pip install eitohforge[firebase]` or `pip install firebase-admin`."
        ) from exc


def build_firebase_push_sender() -> NotificationSender:
    """Return a sender for the ``push`` channel using FCM (device token = ``recipient``).

    Call ``firebase_admin.initialize_app()`` before first use unless using default credentials.
    """

    def send(message: NotificationMessage) -> NotificationResult:
        if message.channel != "push":
            return NotificationResult(
                status="skipped",
                channel=message.channel,
                recipient=message.recipient,
                error_message="Firebase sender only supports push channel",
            )
        messaging = _messaging_module()
        try:
            msg = messaging.Message(
                token=message.recipient,
                notification=messaging.Notification(
                    title=message.subject or "",
                    body=message.body,
                ),
            )
            mid = messaging.send(msg)
        except Exception as exc:
            return NotificationResult(
                status="error",
                channel="push",
                recipient=message.recipient,
                error_message=str(exc),
            )
        return NotificationResult(
            status="sent",
            channel="push",
            recipient=message.recipient,
            provider_message_id=str(mid) if mid else None,
        )

    return send
