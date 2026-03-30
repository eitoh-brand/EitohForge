from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from eitohforge_sdk.infrastructure.jobs import InMemoryBackgroundJobQueue, RetryPolicy


def test_background_job_queue_runs_registered_handler() -> None:
    queue = InMemoryBackgroundJobQueue()
    seen: list[str] = []

    def handler(job: object) -> None:
        seen.append(str(getattr(job, "name")))

    queue.register_handler("email.send", handler)
    queue.enqueue("email.send", payload={"to": "user@acme.dev"})
    results = asyncio.run(queue.run_all_available())

    assert len(results) == 1
    assert results[0].status == "succeeded"
    assert seen == ["email.send"]


def test_background_job_queue_retries_and_then_succeeds() -> None:
    clock = {"now": datetime.now(UTC)}
    queue = InMemoryBackgroundJobQueue(
        retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=2, backoff_multiplier=2.0, max_delay_seconds=10),
        _now_provider=lambda: clock["now"],
    )
    attempts = {"count": 0}

    def flaky_handler(_: object) -> None:
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise RuntimeError("temporary")

    queue.register_handler("invoice.sync", flaky_handler)
    queue.enqueue("invoice.sync")
    clock["now"] = clock["now"] + timedelta(seconds=1)
    first = asyncio.run(queue.run_next())
    assert first is not None
    assert first.status == "retried"

    # first retry is delayed by base_delay_seconds (2s)
    assert asyncio.run(queue.run_next()) is None
    clock["now"] = clock["now"] + timedelta(seconds=2)
    second = asyncio.run(queue.run_next())
    assert second is not None
    assert second.status == "succeeded"
    assert attempts["count"] == 2


def test_background_job_queue_dead_letters_when_retry_budget_exhausted() -> None:
    queue = InMemoryBackgroundJobQueue(retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=0))

    def always_fail(_: object) -> None:
        raise RuntimeError("permanent")

    queue.register_handler("payments.capture", always_fail)
    queue.enqueue("payments.capture")

    first = asyncio.run(queue.run_next())
    assert first is not None
    assert first.status == "retried"

    second = asyncio.run(queue.run_next())
    assert second is not None
    assert second.status == "dead_lettered"
    assert len(queue.dead_letter_jobs) == 1

