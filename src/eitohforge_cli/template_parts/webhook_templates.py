"""Webhook infrastructure template fragments."""

WEBHOOK_FILE_TEMPLATES: dict[str, str] = {
    "app/infrastructure/webhooks/__init__.py": """from app.infrastructure.webhooks.contracts import (
    WebhookDeadLetterRecord,
    WebhookDeliveryResult,
    WebhookEndpointConfig,
    WebhookEvent,
    WebhookRequest,
    WebhookResponse,
    WebhookTransport,
)
from app.infrastructure.webhooks.dispatcher import WebhookDispatcher
from app.infrastructure.webhooks.signing import compute_webhook_signature, verify_webhook_signature
""",
    "app/infrastructure/webhooks/contracts.py": """from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class WebhookEvent:
    name: str
    payload: Mapping[str, object] = field(default_factory=dict)
    metadata: Mapping[str, str] = field(default_factory=dict)
    event_id: str | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class WebhookEndpointConfig:
    url: str
    secret: str
    timeout_seconds: float = 5.0
    signature_header: str = "x-webhook-signature"
    timestamp_header: str = "x-webhook-timestamp"
    event_name_header: str = "x-webhook-event"
    event_id_header: str = "x-webhook-event-id"


@dataclass(frozen=True)
class WebhookRequest:
    url: str
    body: bytes
    headers: Mapping[str, str]
    timeout_seconds: float = 5.0


@dataclass(frozen=True)
class WebhookResponse:
    status_code: int
    body: bytes = b""
    headers: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class WebhookDeadLetterRecord:
    event: WebhookEvent
    endpoint: WebhookEndpointConfig
    attempts: int
    error_message: str | None = None
    last_status_code: int | None = None


@dataclass(frozen=True)
class WebhookDeliveryResult:
    status: str
    attempts: int
    last_status_code: int | None = None
    error_message: str | None = None


WebhookTransportSend = Callable[[WebhookRequest], Awaitable[WebhookResponse] | WebhookResponse]


class WebhookTransport(Protocol):
    def send(self, request: WebhookRequest) -> Awaitable[WebhookResponse] | WebhookResponse:
        ...
""",
    "app/infrastructure/webhooks/signing.py": """from collections.abc import Callable
from datetime import UTC, datetime
import hashlib
import hmac


def compute_webhook_signature(*, timestamp: str, body: bytes, secret: str) -> str:
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
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    now = (now_provider or (lambda: datetime.now(UTC)))()
    if abs(int(now.timestamp()) - ts) > allowed_skew_seconds:
        return False
    expected = compute_webhook_signature(timestamp=timestamp, body=body, secret=secret)
    return hmac.compare_digest(expected, signature)
""",
    "app/infrastructure/webhooks/dispatcher.py": """from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from inspect import isawaitable
import json
from uuid import uuid4

from app.infrastructure.jobs.contracts import RetryPolicy
from app.infrastructure.webhooks.contracts import (
    WebhookDeadLetterRecord,
    WebhookDeliveryResult,
    WebhookEndpointConfig,
    WebhookEvent,
    WebhookRequest,
    WebhookTransport,
)
from app.infrastructure.webhooks.signing import compute_webhook_signature


@dataclass
class WebhookDispatcher:
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    _dead_letters: list[WebhookDeadLetterRecord] = field(default_factory=list)
    _now_provider: Callable[[], datetime] = field(default_factory=lambda: (lambda: datetime.now(UTC)))

    @property
    def dead_letters(self) -> tuple[WebhookDeadLetterRecord, ...]:
        return tuple(self._dead_letters)

    async def dispatch(
        self,
        event: WebhookEvent,
        endpoint: WebhookEndpointConfig,
        *,
        transport: WebhookTransport,
    ) -> WebhookDeliveryResult:
        event_id = event.event_id or str(uuid4())
        body = json.dumps(
            {
                "event_id": event_id,
                "event_name": event.name,
                "payload": event.payload,
                "metadata": event.metadata,
                "occurred_at": event.occurred_at.isoformat(),
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

        last_status_code: int | None = None
        last_error_message: str | None = None
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            timestamp = str(int(self._now_provider().timestamp()))
            signature = compute_webhook_signature(timestamp=timestamp, body=body, secret=endpoint.secret)
            request = WebhookRequest(
                url=endpoint.url,
                body=body,
                timeout_seconds=endpoint.timeout_seconds,
                headers={
                    "content-type": "application/json",
                    endpoint.signature_header: signature,
                    endpoint.timestamp_header: timestamp,
                    endpoint.event_name_header: event.name,
                    endpoint.event_id_header: event_id,
                },
            )
            try:
                response_or_awaitable = transport.send(request)
                response = (
                    await response_or_awaitable
                    if isawaitable(response_or_awaitable)
                    else response_or_awaitable
                )
                last_status_code = response.status_code
                if 200 <= response.status_code < 300:
                    return WebhookDeliveryResult(
                        status="succeeded",
                        attempts=attempt,
                        last_status_code=response.status_code,
                    )
                if not _is_retryable_status(response.status_code):
                    break
            except Exception as exc:
                last_error_message = str(exc)
            if attempt < self.retry_policy.max_attempts:
                continue
            break

        record = WebhookDeadLetterRecord(
            event=event,
            endpoint=endpoint,
            attempts=self.retry_policy.max_attempts,
            error_message=last_error_message,
            last_status_code=last_status_code,
        )
        self._dead_letters.append(record)
        return WebhookDeliveryResult(
            status="dead_lettered",
            attempts=self.retry_policy.max_attempts,
            last_status_code=last_status_code,
            error_message=last_error_message,
        )


def _is_retryable_status(status_code: int) -> bool:
    return status_code == 429 or status_code >= 500
""",
}

