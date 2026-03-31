"""SendGrid HTTP API notification sender (email channel)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from eitohforge_sdk.infrastructure.notifications.contracts import (
    NotificationMessage,
    NotificationResult,
    NotificationSender,
)


def build_sendgrid_email_sender(*, api_key: str, from_email: str) -> NotificationSender:
    """Return a sender callable for the ``email`` channel using SendGrid v3 API."""

    def send(message: NotificationMessage) -> NotificationResult:
        if message.channel != "email":
            return NotificationResult(
                status="skipped",
                channel=message.channel,
                recipient=message.recipient,
                error_message="SendGrid sender only supports email",
            )
        payload = {
            "personalizations": [{"to": [{"email": message.recipient}]}],
            "from": {"email": from_email},
            "subject": message.subject or "(no subject)",
            "content": [{"type": "text/plain", "value": message.body}],
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://api.sendgrid.com/v3/mail/send",
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                _ = resp.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            return NotificationResult(
                status="error",
                channel="email",
                recipient=message.recipient,
                error_message=f"HTTP {exc.code}: {body[:500]}",
            )
        except (urllib.error.URLError, TimeoutError) as exc:
            return NotificationResult(
                status="error",
                channel="email",
                recipient=message.recipient,
                error_message=str(exc),
            )
        return NotificationResult(
            status="sent",
            channel="email",
            recipient=message.recipient,
            provider_message_id=None,
        )

    return send
