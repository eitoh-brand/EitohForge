"""AWS SES (email) and SNS (SMS) senders via ``boto3`` (optional dependency)."""

from __future__ import annotations

import importlib
from typing import Any

from eitohforge_sdk.infrastructure.notifications.contracts import (
    NotificationMessage,
    NotificationResult,
    NotificationSender,
)


def _boto3_client(service: str, **kwargs: Any) -> Any:
    try:
        boto3 = importlib.import_module("boto3")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "AWS notification senders require 'boto3'. Install via `pip install boto3`."
        ) from exc
    return boto3.client(service, **kwargs)


def build_ses_email_sender(*, region: str, from_email: str) -> NotificationSender:
    """Email via Amazon SES ``send_email``."""

    def send(message: NotificationMessage) -> NotificationResult:
        if message.channel != "email":
            return NotificationResult(
                status="skipped",
                channel=message.channel,
                recipient=message.recipient,
                error_message="SES sender only supports email",
            )
        client = _boto3_client("ses", region_name=region)
        try:
            resp = client.send_email(
                Source=from_email,
                Destination={"ToAddresses": [message.recipient]},
                Message={
                    "Subject": {"Data": message.subject or "(no subject)", "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": message.body, "Charset": "UTF-8"}},
                },
            )
        except Exception as exc:
            return NotificationResult(
                status="error",
                channel="email",
                recipient=message.recipient,
                error_message=str(exc),
            )
        mid = resp.get("MessageId") if isinstance(resp, dict) else None
        return NotificationResult(
            status="sent",
            channel="email",
            recipient=message.recipient,
            provider_message_id=str(mid) if mid else None,
        )

    return send


def build_sns_sms_sender(*, region: str) -> NotificationSender:
    """SMS via Amazon SNS ``publish`` to a phone number (E.164)."""

    def send(message: NotificationMessage) -> NotificationResult:
        if message.channel != "sms":
            return NotificationResult(
                status="skipped",
                channel=message.channel,
                recipient=message.recipient,
                error_message="SNS SMS sender only supports sms",
            )
        client = _boto3_client("sns", region_name=region)
        try:
            resp = client.publish(PhoneNumber=message.recipient, Message=message.body)
        except Exception as exc:
            return NotificationResult(
                status="error",
                channel="sms",
                recipient=message.recipient,
                error_message=str(exc),
            )
        mid = resp.get("MessageId") if isinstance(resp, dict) else None
        return NotificationResult(
            status="sent",
            channel="sms",
            recipient=message.recipient,
            provider_message_id=str(mid) if mid else None,
        )

    return send
