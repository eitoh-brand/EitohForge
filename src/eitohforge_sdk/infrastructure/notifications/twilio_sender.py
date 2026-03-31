"""Twilio REST senders for SMS and WhatsApp (``urllib``, no extra dependency)."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request

from eitohforge_sdk.infrastructure.notifications.contracts import (
    NotificationMessage,
    NotificationResult,
    NotificationSender,
)


def _twilio_post(
    account_sid: str,
    auth_token: str,
    path: str,
    form: dict[str, str],
) -> tuple[int, str]:
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/{path}"
    body = urllib.parse.urlencode(form).encode("utf-8")
    token = base64.b64encode(f"{account_sid}:{auth_token}".encode("utf-8")).decode("ascii")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.getcode(), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return exc.code, raw
    except (urllib.error.URLError, TimeoutError) as exc:
        return 0, str(exc)


def build_twilio_sms_sender(*, account_sid: str, auth_token: str, from_number: str) -> NotificationSender:
    """SMS channel using Twilio ``Messages`` API."""

    def send(message: NotificationMessage) -> NotificationResult:
        if message.channel != "sms":
            return NotificationResult(
                status="skipped",
                channel=message.channel,
                recipient=message.recipient,
                error_message="Twilio SMS sender only supports sms channel",
            )
        code, raw = _twilio_post(
            account_sid,
            auth_token,
            "Messages.json",
            {"From": from_number, "To": message.recipient, "Body": message.body},
        )
        if code != 200 and code != 201:
            return NotificationResult(
                status="error",
                channel="sms",
                recipient=message.recipient,
                error_message=f"HTTP {code}: {raw[:500]}",
            )
        mid: str | None = None
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("sid"):
                mid = str(data["sid"])
        except json.JSONDecodeError:
            pass
        return NotificationResult(
            status="sent", channel="sms", recipient=message.recipient, provider_message_id=mid
        )

    return send


def build_twilio_whatsapp_sender(*, account_sid: str, auth_token: str, from_whatsapp: str) -> NotificationSender:
    """WhatsApp channel (Twilio sandbox or approved sender id). ``from_whatsapp`` like ``whatsapp:+14155238886``."""

    def send(message: NotificationMessage) -> NotificationResult:
        if message.channel != "whatsapp":
            return NotificationResult(
                status="skipped",
                channel=message.channel,
                recipient=message.recipient,
                error_message="Twilio WhatsApp sender only supports whatsapp channel",
            )
        to = message.recipient if message.recipient.startswith("whatsapp:") else f"whatsapp:{message.recipient}"
        code, raw = _twilio_post(
            account_sid,
            auth_token,
            "Messages.json",
            {"From": from_whatsapp, "To": to, "Body": message.body},
        )
        if code != 200 and code != 201:
            return NotificationResult(
                status="error",
                channel="whatsapp",
                recipient=message.recipient,
                error_message=f"HTTP {code}: {raw[:500]}",
            )
        return NotificationResult(status="sent", channel="whatsapp", recipient=message.recipient)

    return send
