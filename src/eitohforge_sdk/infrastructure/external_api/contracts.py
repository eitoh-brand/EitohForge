"""External API client contracts."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Literal, Protocol

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


@dataclass(frozen=True)
class ApiRequest:
    """Transport-agnostic outbound API request envelope."""

    method: HttpMethod
    url: str
    headers: Mapping[str, str] = field(default_factory=dict)
    query: Mapping[str, str] = field(default_factory=dict)
    body: bytes | None = None
    timeout_seconds: float = 10.0


@dataclass(frozen=True)
class ApiResponse:
    """Transport-agnostic API response envelope."""

    status_code: int
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes = b""


@dataclass(frozen=True)
class RetryStrategy:
    """Retry strategy for outbound API calls."""

    max_attempts: int = 3
    base_delay_seconds: float = 0.5
    backoff_multiplier: float = 2.0
    max_delay_seconds: float = 8.0
    retry_status_codes: tuple[int, ...] = (408, 429, 500, 502, 503, 504)
    retry_methods: tuple[HttpMethod, ...] = ("GET", "HEAD", "OPTIONS", "PUT", "DELETE")

    def delay_for_attempt(self, attempt: int) -> float:
        if attempt <= 1:
            return 0.0
        exponent = max(0, attempt - 2)
        delay = self.base_delay_seconds * (self.backoff_multiplier**exponent)
        return max(0.0, min(self.max_delay_seconds, delay))


@dataclass(frozen=True)
class CircuitBreakerSettings:
    """Circuit breaker thresholds for outbound API calls."""

    failure_threshold: int = 5
    recovery_timeout_seconds: int = 30


@dataclass(frozen=True)
class ApiCallResult:
    """Normalized result from resilient external API call."""

    status: str
    attempts: int
    circuit_state: str
    response: ApiResponse | None = None
    error_message: str | None = None


ExternalApiTransportSend = Callable[[ApiRequest], Awaitable[ApiResponse] | ApiResponse]


class ExternalApiTransport(Protocol):
    """Transport adapter used by resilient external API client."""

    def send(self, request: ApiRequest) -> Awaitable[ApiResponse] | ApiResponse:
        ...

