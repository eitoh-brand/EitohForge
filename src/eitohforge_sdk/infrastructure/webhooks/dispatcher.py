"""Webhook dispatcher with retry policy and dead-letter queue."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from inspect import isawaitable
import json
from uuid import uuid4

from eitohforge_sdk.infrastructure.jobs import RetryPolicy
from eitohforge_sdk.infrastructure.webhooks.contracts import (
    WebhookDeadLetterRecord,
    WebhookDeliveryResult,
    WebhookEndpointConfig,
    WebhookEvent,
    WebhookRequest,
    WebhookTransport,
)
from eitohforge_sdk.infrastructure.webhooks.signing import compute_webhook_signature


@dataclass
class WebhookDispatcher:
    """Dispatches signed webhooks with retries and dead-letter support."""

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

