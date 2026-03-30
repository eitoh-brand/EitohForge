from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from eitohforge_sdk.infrastructure.external_api import (
    ApiRequest,
    ApiResponse,
    CircuitBreakerSettings,
    ResilientExternalApiClient,
    RetryStrategy,
)


def test_external_api_client_retries_until_success() -> None:
    calls = {"count": 0}

    class FlakyTransport:
        def send(self, _: ApiRequest) -> ApiResponse:
            calls["count"] += 1
            if calls["count"] < 3:
                return ApiResponse(status_code=503)
            return ApiResponse(status_code=200, body=b"ok")

    client = ResilientExternalApiClient(
        retry_strategy=RetryStrategy(max_attempts=3, base_delay_seconds=0.0),
        _sleep=lambda _: asyncio.sleep(0),
    )
    result = asyncio.run(client.call(ApiRequest(method="GET", url="https://example.com"), transport=FlakyTransport()))
    assert result.status == "succeeded"
    assert result.attempts == 3
    assert result.response is not None and result.response.status_code == 200


def test_external_api_client_opens_circuit_after_threshold() -> None:
    clock = {"now": datetime(2026, 1, 1, tzinfo=UTC)}

    class FailingTransport:
        def __init__(self) -> None:
            self.calls = 0

        def send(self, _: ApiRequest) -> ApiResponse:
            self.calls += 1
            return ApiResponse(status_code=500)

    transport = FailingTransport()
    client = ResilientExternalApiClient(
        retry_strategy=RetryStrategy(max_attempts=1, base_delay_seconds=0.0),
        circuit_breaker=CircuitBreakerSettings(failure_threshold=2, recovery_timeout_seconds=60),
        _now_provider=lambda: clock["now"],
        _sleep=lambda _: asyncio.sleep(0),
    )
    req = ApiRequest(method="GET", url="https://example.com")
    first = asyncio.run(client.call(req, transport=transport))
    second = asyncio.run(client.call(req, transport=transport))
    third = asyncio.run(client.call(req, transport=transport))

    assert first.status == "failed"
    assert second.status == "failed"
    assert third.status == "short_circuited"
    assert transport.calls == 2


def test_external_api_client_allows_half_open_recovery() -> None:
    clock = {"now": datetime(2026, 1, 1, tzinfo=UTC)}
    state = {"first": True}

    class RecoveringTransport:
        def send(self, _: ApiRequest) -> ApiResponse:
            if state["first"]:
                state["first"] = False
                return ApiResponse(status_code=500)
            return ApiResponse(status_code=200)

    client = ResilientExternalApiClient(
        retry_strategy=RetryStrategy(max_attempts=1, base_delay_seconds=0.0),
        circuit_breaker=CircuitBreakerSettings(failure_threshold=1, recovery_timeout_seconds=10),
        _now_provider=lambda: clock["now"],
        _sleep=lambda _: asyncio.sleep(0),
    )
    request = ApiRequest(method="GET", url="https://example.com")
    failed = asyncio.run(client.call(request, transport=RecoveringTransport()))
    assert failed.status == "failed"
    assert failed.circuit_state == "open"

    # still open before timeout
    early = asyncio.run(client.call(request, transport=RecoveringTransport()))
    assert early.status == "short_circuited"

    # move to half-open window and succeed; circuit should close
    clock["now"] = clock["now"] + timedelta(seconds=11)
    recovered = asyncio.run(client.call(request, transport=RecoveringTransport()))
    assert recovered.status == "succeeded"
    assert recovered.circuit_state == "closed"

