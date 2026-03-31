"""Inbound webhook HTTP receiver with HMAC verification."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import hashlib
import hmac
import json
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Request, status

from eitohforge_sdk.infrastructure.webhooks.signing import verify_webhook_signature


def verify_body_hmac_hex(*, secret: str, body: bytes, signature_hex: str) -> bool:
    """Verify ``signature_hex`` is HMAC-SHA256(body, secret) as lowercase hex."""
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_hex.strip())


def register_inbound_webhook_router(
    app: FastAPI,
    *,
    path: str = "/webhooks/inbound",
    secret: str,
    signature_header: str = "X-Webhook-Signature",
    timestamp_header: str = "X-Webhook-Timestamp",
    use_timestamp_canonical: bool = True,
    handler: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
) -> APIRouter:
    """Register ``POST`` endpoint that verifies HMAC then passes parsed JSON to ``handler``.

    When ``use_timestamp_canonical`` is True (default), signatures follow the same
    ``timestamp + "." + body`` scheme as `compute_webhook_signature`. Otherwise a
    plain HMAC-SHA256(body) hex digest is expected in ``signature_header``.
    """

    router = APIRouter()

    @router.post(path)
    async def receive(request: Request) -> dict[str, Any]:
        body = await request.body()
        sig = request.headers.get(signature_header)
        if not sig:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature")
        if use_timestamp_canonical:
            ts = request.headers.get(timestamp_header)
            if not ts:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing timestamp")
            if not verify_webhook_signature(signature=sig, timestamp=ts, body=body, secret=secret):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")
        else:
            if not verify_body_hmac_hex(secret=secret, body=body, signature_hex=sig):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON must be an object")
        if handler is not None:
            await handler(payload)
        return {"success": True, "received": True}

    app.include_router(router)
    return router
