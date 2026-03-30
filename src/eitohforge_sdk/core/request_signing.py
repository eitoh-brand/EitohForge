"""Request signing middleware with replay/tamper protection."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
from typing import Protocol

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response


@dataclass(frozen=True)
class RequestSigningRule:
    """Request signing configuration."""

    enabled: bool = True
    signature_header: str = "x-signature"
    timestamp_header: str = "x-signature-timestamp"
    nonce_header: str = "x-signature-nonce"
    key_id_header: str = "x-signature-key-id"
    allowed_skew_seconds: int = 300
    nonce_ttl_seconds: int = 300
    methods: tuple[str, ...] = ("POST", "PUT", "PATCH", "DELETE")
    scope_path_prefix: str | None = None


@dataclass(frozen=True)
class SignaturePayload:
    """Canonical payload fields used for request signing."""

    method: str
    path: str
    timestamp: str
    nonce: str
    body_sha256_hex: str


class RequestNonceStore(Protocol):
    """Replay nonce store contract."""

    def mark(self, nonce_key: str, *, expires_at: datetime) -> bool:
        ...


class InMemoryRequestNonceStore:
    """In-memory nonce store preventing replay within TTL."""

    def __init__(self, now_provider: Callable[[], datetime] | None = None) -> None:
        self._records: dict[str, datetime] = {}
        self._now_provider = now_provider or (lambda: datetime.now(UTC))

    def mark(self, nonce_key: str, *, expires_at: datetime) -> bool:
        now = self._now_provider()
        self._prune(now)
        if nonce_key in self._records:
            return False
        self._records[nonce_key] = expires_at
        return True

    def _prune(self, now: datetime) -> None:
        for key in tuple(self._records):
            if self._records[key] <= now:
                self._records.pop(key, None)


def compute_request_signature(payload: SignaturePayload, *, secret: str) -> str:
    """Compute canonical HMAC signature for a request payload."""
    canonical = (
        f"{payload.method}\n"
        f"{payload.path}\n"
        f"{payload.timestamp}\n"
        f"{payload.nonce}\n"
        f"{payload.body_sha256_hex}"
    ).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()


def register_request_signing_middleware(
    app: FastAPI,
    rule: RequestSigningRule,
    *,
    resolve_secret: Callable[[str | None], str | None],
    nonce_store: RequestNonceStore | None = None,
    now_provider: Callable[[], datetime] | None = None,
) -> RequestNonceStore:
    """Register request-signing middleware."""
    resolved_nonce_store = nonce_store or InMemoryRequestNonceStore(now_provider=now_provider)
    resolved_now_provider = now_provider or (lambda: datetime.now(UTC))

    @app.middleware("http")
    async def _request_signing_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not rule.enabled:
            return await call_next(request)
        if request.method.upper() not in {method.upper() for method in rule.methods}:
            return await call_next(request)
        if rule.scope_path_prefix is not None and not request.url.path.startswith(rule.scope_path_prefix):
            return await call_next(request)

        signature = request.headers.get(rule.signature_header)
        timestamp = request.headers.get(rule.timestamp_header)
        nonce = request.headers.get(rule.nonce_header)
        key_id = request.headers.get(rule.key_id_header)
        if not signature or not timestamp or not nonce:
            return _signature_error("MISSING_SIGNATURE_HEADERS", "Missing signature headers.")

        try:
            request_ts = int(timestamp)
        except ValueError:
            return _signature_error("INVALID_SIGNATURE_TIMESTAMP", "Invalid signature timestamp.")

        now = resolved_now_provider()
        now_ts = int(now.timestamp())
        if abs(now_ts - request_ts) > rule.allowed_skew_seconds:
            return _signature_error("STALE_SIGNATURE_TIMESTAMP", "Signature timestamp outside allowed skew.")

        nonce_key = f"{key_id or 'default'}:{nonce}"
        nonce_expires_at = now + timedelta(seconds=rule.nonce_ttl_seconds)
        if not resolved_nonce_store.mark(nonce_key, expires_at=nonce_expires_at):
            return _signature_error("REPLAYED_SIGNATURE_NONCE", "Signature nonce has already been used.")

        secret = resolve_secret(key_id)
        if not secret:
            return _signature_error("UNKNOWN_SIGNATURE_KEY", "Unknown request-signing key id.")

        body = await request.body()
        payload = SignaturePayload(
            method=request.method.upper(),
            path=request.url.path,
            timestamp=timestamp,
            nonce=nonce,
            body_sha256_hex=hashlib.sha256(body).hexdigest(),
        )
        expected = compute_request_signature(payload, secret=secret)
        if not hmac.compare_digest(expected, signature):
            return _signature_error("INVALID_REQUEST_SIGNATURE", "Request signature verification failed.")

        return await call_next(request)

    return resolved_nonce_store


def _signature_error(code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"success": False, "error": {"code": code, "message": message}},
    )

