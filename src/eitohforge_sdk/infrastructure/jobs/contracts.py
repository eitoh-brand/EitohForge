"""Background job contracts and retry policy primitives."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class RetryPolicy:
    """Retry policy for failed background jobs."""

    max_attempts: int = 3
    base_delay_seconds: int = 1
    backoff_multiplier: float = 2.0
    max_delay_seconds: int = 60

    def delay_for_attempt(self, attempt: int) -> int:
        """Compute delay seconds for the next retry attempt."""
        if attempt <= 1:
            return 0
        exponent = max(0, attempt - 2)
        delay = int(self.base_delay_seconds * (self.backoff_multiplier**exponent))
        return max(0, min(self.max_delay_seconds, delay))


@dataclass(frozen=True)
class JobEnvelope:
    """Canonical job payload stored in the queue."""

    id: str
    name: str
    payload: Mapping[str, object] = field(default_factory=dict)
    metadata: Mapping[str, str] = field(default_factory=dict)
    attempts: int = 0
    available_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class JobResult:
    """Execution outcome of a single job run."""

    job_id: str
    name: str
    status: str
    attempts: int
    error_message: str | None = None


JobHandler = Callable[[JobEnvelope], Awaitable[None] | None]


class BackgroundJobQueue(Protocol):
    """Background job queue adapter contract."""

    def register_handler(self, job_name: str, handler: JobHandler) -> None:
        ...

    def enqueue(
        self,
        job_name: str,
        *,
        payload: Mapping[str, object] | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> JobEnvelope:
        ...

    async def run_next(self) -> JobResult | None:
        ...

    async def run_all_available(self) -> tuple[JobResult, ...]:
        ...

