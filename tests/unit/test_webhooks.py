from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from eitohforge_sdk.infrastructure.jobs import RetryPolicy
from eitohforge_sdk.infrastructure.webhooks import (
    WebhookDispatcher,
    WebhookEndpointConfig,
    WebhookEvent,
    WebhookRequest,
    WebhookResponse,
    compute_webhook_signature,
    verify_webhook_signature,
)


def test_webhook_signature_roundtrip_and_tamper_detection() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    timestamp = str(int(now.timestamp()))
    body = b'{"hello":"world"}'
    secret = "webhook-secret"
    signature = compute_webhook_signature(timestamp=timestamp, body=body, secret=secret)

    assert (
        verify_webhook_signature(
            signature=signature,
            timestamp=timestamp,
            body=body,
            secret=secret,
            now_provider=lambda: now,
        )
        is True
    )
    assert (
        verify_webhook_signature(
            signature=signature,
            timestamp=timestamp,
            body=b'{"hello":"tampered"}',
            secret=secret,
            now_provider=lambda: now,
        )
        is False
    )


def test_webhook_dispatcher_retries_then_dead_letters() -> None:
    dispatcher = WebhookDispatcher(retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=0))
    endpoint = WebhookEndpointConfig(url="https://example.com/hook", secret="s")
    event = WebhookEvent(name="order.created", payload={"id": "o1"})

    class Always500Transport:
        def __init__(self) -> None:
            self.requests: list[WebhookRequest] = []

        def send(self, request: WebhookRequest) -> WebhookResponse:
            self.requests.append(request)
            return WebhookResponse(status_code=500)

    transport = Always500Transport()
    result = asyncio.run(dispatcher.dispatch(event, endpoint, transport=transport))
    assert result.status == "dead_lettered"
    assert result.attempts == 3
    assert len(transport.requests) == 3
    assert len(dispatcher.dead_letters) == 1


def test_webhook_dispatcher_marks_success_with_signed_headers() -> None:
    dispatcher = WebhookDispatcher(retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=0))
    endpoint = WebhookEndpointConfig(url="https://example.com/hook", secret="s3cr3t")
    event = WebhookEvent(name="invoice.paid", payload={"invoice_id": "inv-1"}, event_id="evt-1")

    class SuccessTransport:
        def __init__(self) -> None:
            self.last_request: WebhookRequest | None = None

        async def send(self, request: WebhookRequest) -> WebhookResponse:
            self.last_request = request
            return WebhookResponse(status_code=202)

    transport = SuccessTransport()
    result = asyncio.run(dispatcher.dispatch(event, endpoint, transport=transport))
    assert result.status == "succeeded"
    assert transport.last_request is not None
    assert endpoint.signature_header in transport.last_request.headers
    assert endpoint.timestamp_header in transport.last_request.headers
    assert transport.last_request.headers[endpoint.event_name_header] == "invoice.paid"
    assert transport.last_request.headers[endpoint.event_id_header] == "evt-1"

