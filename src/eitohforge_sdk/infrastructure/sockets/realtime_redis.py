"""Redis subscriber loop for cluster-wide realtime broadcast (used with ``build_forge_app`` lifespan)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from fastapi import FastAPI

from eitohforge_sdk.core.config import AppSettings
from eitohforge_sdk.infrastructure.sockets.redis_hub import dispatch_redis_fanout_payload

logger = logging.getLogger(__name__)


async def run_realtime_redis_subscriber(
    app: FastAPI,
    *,
    settings_provider: Callable[[], AppSettings],
    stop: asyncio.Event,
) -> None:
    """Subscribe to ``RealtimeSettings.redis_broadcast_channel`` and fan out to ``app.state.socket_hub``."""
    settings = settings_provider()
    url = settings.realtime.redis_url
    channel = settings.realtime.redis_broadcast_channel
    if not url:
        return

    import redis.asyncio as redis_async

    client = redis_async.from_url(url, decode_responses=True)
    app.state._realtime_redis_subscribe_client = client
    pubsub = client.pubsub()
    await pubsub.subscribe(channel)
    try:
        while not stop.is_set():
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
            if msg is None:
                continue
            if msg.get("type") != "message":
                continue
            data = msg.get("data")
            if not isinstance(data, str):
                continue
            hub = getattr(app.state, "socket_hub", None)
            if hub is None:
                continue
            try:
                await dispatch_redis_fanout_payload(hub, data)
            except Exception:
                logger.exception("realtime Redis fan-out delivery failed")
    finally:
        try:
            await pubsub.unsubscribe(channel)
        except Exception:
            logger.debug("pubsub unsubscribe failed", exc_info=True)
        try:
            await pubsub.close()
        except Exception:
            logger.debug("pubsub close failed", exc_info=True)
        try:
            await client.aclose()
        except Exception:
            logger.debug("redis subscribe client aclose failed", exc_info=True)
        if hasattr(app.state, "_realtime_redis_subscribe_client"):
            delattr(app.state, "_realtime_redis_subscribe_client")
