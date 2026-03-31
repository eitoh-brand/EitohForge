"""Dramatiq-backed job publisher (optional ``dramatiq`` dependency)."""

from __future__ import annotations

import importlib
import inspect
import json
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from eitohforge_sdk.infrastructure.jobs.contracts import JobEnvelope, JobHandler, JobPublisher

_handlers: dict[str, JobHandler] = {}
_actor: Any = None


def _require_dramatiq() -> Any:
    try:
        return importlib.import_module("dramatiq")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Dramatiq job publisher requires 'dramatiq'. Install via `pip install eitohforge[jobs-dramatiq]` "
            "or `pip install dramatiq`."
        ) from exc


def _ensure_actor(dramatiq: Any) -> Any:
    global _actor
    if _actor is not None:
        return _actor

    @dramatiq.actor(queue_name="eitohforge", max_retries=0)
    def dispatch_job(
        job_name: str,
        job_id: str,
        payload_json: str,
        metadata_json: str,
    ) -> None:
        raw = json.loads(payload_json)
        meta = json.loads(metadata_json)
        handler = _handlers.get(job_name)
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

            asyncio.run(maybe)

    _actor = dispatch_job
    return _actor


class DramatiqJobPublisher(JobPublisher):
    """Publish jobs via a shared Dramatiq actor. Handlers live in a process-wide registry."""

    def __init__(self, broker: Any | None = None) -> None:
        dramatiq = _require_dramatiq()
        if broker is not None:
            dramatiq.set_broker(broker)
        self._actor = _ensure_actor(dramatiq)

    def register_handler(self, job_name: str, handler: JobHandler) -> None:
        _handlers[job_name] = handler

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
        self._actor.send(
            job_name,
            envelope.id,
            json.dumps(dict(envelope.payload), default=str),
            json.dumps(dict(envelope.metadata)),
        )
        return envelope
