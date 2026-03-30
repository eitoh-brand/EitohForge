"""Resilient external API client with retry/circuit breaker."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from inspect import isawaitable

from eitohforge_sdk.infrastructure.external_api.contracts import (
    ApiCallResult,
    ApiRequest,
    ApiResponse,
    CircuitBreakerSettings,
    ExternalApiTransport,
    RetryStrategy,
)


@dataclass
class ResilientExternalApiClient:
    """External API client implementing retries and circuit-breaker behavior."""

    retry_strategy: RetryStrategy = field(default_factory=RetryStrategy)
    circuit_breaker: CircuitBreakerSettings = field(default_factory=CircuitBreakerSettings)
    _now_provider: Callable[[], datetime] = field(default_factory=lambda: (lambda: datetime.now(UTC)))
    _sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
    _failure_count: int = 0
    _opened_at: datetime | None = None

    async def call(self, request: ApiRequest, *, transport: ExternalApiTransport) -> ApiCallResult:
        now = self._now_provider()
        state = self._state(now)
        if state == "open":
            return ApiCallResult(
                status="short_circuited",
                attempts=0,
                circuit_state=state,
                error_message="Circuit breaker is open.",
            )

        attempts = 0
        last_response: ApiResponse | None = None
        last_error_message: str | None = None
        max_attempts = max(1, self.retry_strategy.max_attempts)
        allow_retries = state != "half_open" and request.method in set(self.retry_strategy.retry_methods)

        for attempt in range(1, max_attempts + 1):
            attempts = attempt
            try:
                response_or_awaitable = transport.send(request)
                response = (
                    await response_or_awaitable
                    if isawaitable(response_or_awaitable)
                    else response_or_awaitable
                )
                last_response = response
                if 200 <= response.status_code < 300:
                    self._on_success()
                    return ApiCallResult(
                        status="succeeded",
                        attempts=attempts,
                        circuit_state=self._state(self._now_provider()),
                        response=response,
                    )
                if not (allow_retries and response.status_code in set(self.retry_strategy.retry_status_codes)):
                    break
            except Exception as exc:
                last_error_message = str(exc)
                if not allow_retries:
                    break

            if attempt < max_attempts:
                delay = self.retry_strategy.delay_for_attempt(attempt + 1)
                if delay > 0:
                    await self._sleep(delay)
                continue
            break

        self._on_failure()
        return ApiCallResult(
            status="failed",
            attempts=attempts,
            circuit_state=self._state(self._now_provider()),
            response=last_response,
            error_message=last_error_message,
        )

    def _state(self, now: datetime) -> str:
        if self._opened_at is None:
            return "closed"
        elapsed = (now - self._opened_at).total_seconds()
        if elapsed >= self.circuit_breaker.recovery_timeout_seconds:
            return "half_open"
        return "open"

    def _on_success(self) -> None:
        self._failure_count = 0
        self._opened_at = None

    def _on_failure(self) -> None:
        now = self._now_provider()
        state = self._state(now)
        if state == "half_open":
            self._failure_count = self.circuit_breaker.failure_threshold
            self._opened_at = now
            return
        self._failure_count += 1
        if self._failure_count >= self.circuit_breaker.failure_threshold:
            self._opened_at = now

