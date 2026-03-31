"""Celery-backed job publisher (optional ``celery`` dependency)."""

from __future__ import annotations

import importlib
import inspect
import json
from collections.abc import Mapping
from typing import Any, Coroutine, cast
from uuid import uuid4

from eitohforge_sdk.infrastructure.jobs.contracts import JobEnvelope, JobHandler, JobPublisher


def _require_celery() -> Any:
    try:
        return importlib.import_module("celery")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Celery job publisher requires 'celery'. Install via `pip install eitohforge[jobs-celery]` "
            "or `pip install celery`."
        ) from exc


class CeleryJobPublisher(JobPublisher):
    """Publish jobs to a Celery app. Workers must register the same handlers before consuming."""

    def __init__(self, celery_app: Any) -> None:
        _require_celery()
        self._app = celery_app
        self._handlers: dict[str, JobHandler] = {}
        self._task = self._create_dispatch_task()

    def _create_dispatch_task(self) -> Any:
        handlers = self._handlers

        @self._app.task(name="eitohforge_sdk.celery_dispatch", ignore_result=True)  # type: ignore[untyped-decorator]
        def dispatch_job(job_name: str, job_id: str, payload_json: str, metadata_json: str) -> None:
            raw = json.loads(payload_json)
            meta = json.loads(metadata_json)
            handler = handlers.get(job_name)
            if handler is None:
                return
            envelope = JobEnvelope(
                id=job_id,
                name=job_name,
                payload=raw,
                metadata=meta,
            )
            maybe = handler(envelope)
            if inspect.isawaitable(maybe):
                import asyncio

                coro = cast(Coroutine[Any, Any, None], maybe)
                asyncio.run(coro)

        return dispatch_job

    def register_handler(self, job_name: str, handler: JobHandler) -> None:
        self._handlers[job_name] = handler

    def enqueue(
        self,
        job_name: str,
        *,
        payload: Mapping[str, object] | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> JobEnvelope:
        envelope = JobEnvelope(
            id=str(uuid4()),
            name=job_name,
            payload=payload or {},
            metadata=metadata or {},
        )
        self._task.delay(
            job_name,
            envelope.id,
            json.dumps(dict(envelope.payload), default=str),
            json.dumps(dict(envelope.metadata)),
        )
        return envelope
