"""Background job infrastructure template fragments."""

JOBS_FILE_TEMPLATES: dict[str, str] = {
    "app/infrastructure/jobs/__init__.py": """from app.infrastructure.jobs.contracts import (
    BackgroundJobQueue,
    JobEnvelope,
    JobHandler,
    JobResult,
    RetryPolicy,
)
from app.infrastructure.jobs.memory import InMemoryBackgroundJobQueue
""",
    "app/infrastructure/jobs/contracts.py": """from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: int = 1
    backoff_multiplier: float = 2.0
    max_delay_seconds: int = 60

    def delay_for_attempt(self, attempt: int) -> int:
        if attempt <= 1:
            return 0
        exponent = max(0, attempt - 2)
        delay = int(self.base_delay_seconds * (self.backoff_multiplier**exponent))
        return max(0, min(self.max_delay_seconds, delay))


@dataclass(frozen=True)
class JobEnvelope:
    id: str
    name: str
    payload: Mapping[str, object] = field(default_factory=dict)
    metadata: Mapping[str, str] = field(default_factory=dict)
    attempts: int = 0
    available_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class JobResult:
    job_id: str
    name: str
    status: str
    attempts: int
    error_message: str | None = None


JobHandler = Callable[[JobEnvelope], Awaitable[None] | None]


class BackgroundJobQueue(Protocol):
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
""",
    "app/infrastructure/jobs/memory.py": """from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from inspect import isawaitable
from uuid import uuid4

from app.infrastructure.jobs.contracts import JobEnvelope, JobHandler, JobResult, RetryPolicy


@dataclass
class InMemoryBackgroundJobQueue:
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    _handlers: dict[str, JobHandler] = field(default_factory=dict)
    _pending: deque[JobEnvelope] = field(default_factory=deque)
    _dead_letter: list[JobEnvelope] = field(default_factory=list)
    _now_provider: Callable[[], datetime] = field(default_factory=lambda: (lambda: datetime.now(UTC)))

    @property
    def dead_letter_jobs(self) -> tuple[JobEnvelope, ...]:
        return tuple(self._dead_letter)

    def register_handler(self, job_name: str, handler: JobHandler) -> None:
        self._handlers[job_name] = handler

    def enqueue(
        self,
        job_name: str,
        *,
        payload: dict[str, object] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> JobEnvelope:
        envelope = JobEnvelope(
            id=str(uuid4()),
            name=job_name,
            payload=payload or {},
            metadata=metadata or {},
        )
        self._pending.append(envelope)
        return envelope

    async def run_next(self) -> JobResult | None:
        if not self._pending:
            return None
        now = self._now_provider()
        job = self._pending[0]
        if job.available_at > now:
            return None
        self._pending.popleft()
        return await self._dispatch(job)

    async def run_all_available(self) -> tuple[JobResult, ...]:
        results: list[JobResult] = []
        while True:
            result = await self.run_next()
            if result is None:
                break
            results.append(result)
        return tuple(results)

    async def _dispatch(self, job: JobEnvelope) -> JobResult:
        handler = self._handlers.get(job.name)
        if handler is None:
            failed = self._mark_dead_letter(job)
            return JobResult(
                job_id=failed.id,
                name=failed.name,
                status="dead_lettered",
                attempts=failed.attempts,
                error_message=f"No handler registered for job: {failed.name}",
            )

        next_attempt = job.attempts + 1
        executing = replace(job, attempts=next_attempt)
        try:
            maybe_awaitable = handler(executing)
            if isawaitable(maybe_awaitable):
                await maybe_awaitable
            return JobResult(
                job_id=executing.id,
                name=executing.name,
                status="succeeded",
                attempts=executing.attempts,
            )
        except Exception as exc:
            if next_attempt >= self.retry_policy.max_attempts:
                failed = self._mark_dead_letter(executing)
                return JobResult(
                    job_id=failed.id,
                    name=failed.name,
                    status="dead_lettered",
                    attempts=failed.attempts,
                    error_message=str(exc),
                )
            delay_seconds = self.retry_policy.delay_for_attempt(next_attempt + 1)
            retried = replace(
                executing,
                available_at=self._now_provider() + timedelta(seconds=delay_seconds),
            )
            self._pending.append(retried)
            return JobResult(
                job_id=retried.id,
                name=retried.name,
                status="retried",
                attempts=retried.attempts,
                error_message=str(exc),
            )

    def _mark_dead_letter(self, job: JobEnvelope) -> JobEnvelope:
        self._dead_letter.append(job)
        return job
""",
}

