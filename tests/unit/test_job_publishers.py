from __future__ import annotations

import pytest

from eitohforge_sdk.infrastructure.jobs.celery_publisher import CeleryJobPublisher


def test_celery_job_publisher_eager_executes_handler() -> None:
    pytest.importorskip("celery")
    from celery import Celery

    app = Celery("eitohforge_test", broker="memory://")
    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True

    pub = CeleryJobPublisher(app)
    seen: list[object] = []

    def handler(env: object) -> None:
        seen.append(env)

    pub.register_handler("ping", handler)
    pub.enqueue("ping", payload={"x": 1})
    assert len(seen) == 1
    assert getattr(seen[0], "payload") == {"x": 1}
