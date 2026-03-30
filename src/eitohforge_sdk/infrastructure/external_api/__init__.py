"""External API client primitives."""

from eitohforge_sdk.infrastructure.external_api.client import ResilientExternalApiClient
from eitohforge_sdk.infrastructure.external_api.contracts import (
    ApiCallResult,
    ApiRequest,
    ApiResponse,
    CircuitBreakerSettings,
    ExternalApiTransport,
    ExternalApiTransportSend,
    HttpMethod,
    RetryStrategy,
)

__all__ = [
    "HttpMethod",
    "ApiRequest",
    "ApiResponse",
    "RetryStrategy",
    "CircuitBreakerSettings",
    "ApiCallResult",
    "ExternalApiTransport",
    "ExternalApiTransportSend",
    "ResilientExternalApiClient",
]

