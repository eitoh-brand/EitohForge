"""SMTP email sender (stdlib ``smtplib``)."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from eitohforge_sdk.infrastructure.notifications.contracts import (
    NotificationMessage,
    NotificationResult,
    NotificationSender,
)


def build_smtp_email_sender(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    from_email: str,
    use_tls: bool = True,
) -> NotificationSender:
    """Return a synchronous sender for the ``email`` channel."""

    def send(message: NotificationMessage) -> NotificationResult:
        if message.channel != "email":
            return NotificationResult(
                status="skipped",
                channel=message.channel,
                recipient=message.recipient,
                error_message="SMTP sender only supports email",
            )
        msg = EmailMessage()
        msg["From"] = from_email
        msg["To"] = message.recipient
        msg["Subject"] = message.subject or "(no subject)"
        msg.set_content(message.body)
        try:
            with smtplib.SMTP(host, port, timeout=30) as smtp:
                if use_tls:
                    smtp.starttls()
                smtp.login(username, password)
                smtp.send_message(msg)
        except OSError as exc:
            return NotificationResult(
                status="error",
                channel="email",
                recipient=message.recipient,
                error_message=str(exc),
            )
        return NotificationResult(status="sent", channel="email", recipient=message.recipient)

    return send
