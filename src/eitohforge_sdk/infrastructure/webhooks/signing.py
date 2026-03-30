"""Webhook signature helpers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import hashlib
import hmac


def compute_webhook_signature(*, timestamp: str, body: bytes, secret: str) -> str:
    """Compute HMAC SHA-256 signature for webhook payload."""
    canonical = timestamp.encode("utf-8") + b"." + body
    return hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()


def verify_webhook_signature(
    *,
    signature: str,
    timestamp: str,
    body: bytes,
    secret: str,
    allowed_skew_seconds: int = 300,
    now_provider: Callable[[], datetime] | None = None,
) -> bool:
    """Verify webhook signature and timestamp freshness."""
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    now = (now_provider or (lambda: datetime.now(UTC)))()
    if abs(int(now.timestamp()) - ts) > allowed_skew_seconds:
        return False
    expected = compute_webhook_signature(timestamp=timestamp, body=body, secret=secret)
    return hmac.compare_digest(expected, signature)

