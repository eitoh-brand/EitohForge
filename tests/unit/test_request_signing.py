from __future__ import annotations

from datetime import UTC, datetime
import hashlib

from fastapi import FastAPI
from fastapi.testclient import TestClient

from eitohforge_sdk.core.request_signing import (
    RequestSigningRule,
    SignaturePayload,
    compute_request_signature,
    register_request_signing_middleware,
)


def _signed_headers(*, path: str, method: str, body: bytes, secret: str, timestamp: str, nonce: str) -> dict[str, str]:
    payload = SignaturePayload(
        method=method,
        path=path,
        timestamp=timestamp,
        nonce=nonce,
        body_sha256_hex=hashlib.sha256(body).hexdigest(),
    )
    signature = compute_request_signature(payload, secret=secret)
    return {
        "x-signature": signature,
        "x-signature-timestamp": timestamp,
        "x-signature-nonce": nonce,
        "x-signature-key-id": "default",
        "content-type": "application/json",
    }


def test_request_signing_accepts_valid_signature() -> None:
    app = FastAPI()
    register_request_signing_middleware(
        app,
        RequestSigningRule(),
        resolve_secret=lambda key_id: "super-secret" if key_id == "default" else None,
        now_provider=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    @app.post("/signed")
    def signed(payload: dict[str, int]) -> dict[str, int]:
        return {"ok": payload["value"]}

    client = TestClient(app)
    body = b'{"value":1}'
    headers = _signed_headers(
        path="/signed",
        method="POST",
        body=body,
        secret="super-secret",
        timestamp=str(int(datetime(2026, 1, 1, 12, 0, tzinfo=UTC).timestamp())),
        nonce="n1",
    )
    response = client.post("/signed", content=body, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"ok": 1}


def test_request_signing_rejects_replayed_nonce() -> None:
    app = FastAPI()
    register_request_signing_middleware(
        app,
        RequestSigningRule(),
        resolve_secret=lambda _: "super-secret",
        now_provider=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    @app.post("/signed")
    def signed(payload: dict[str, int]) -> dict[str, int]:
        return {"ok": payload["value"]}

    client = TestClient(app)
    body = b'{"value":2}'
    headers = _signed_headers(
        path="/signed",
        method="POST",
        body=body,
        secret="super-secret",
        timestamp=str(int(datetime(2026, 1, 1, 12, 0, tzinfo=UTC).timestamp())),
        nonce="same-nonce",
    )
    assert client.post("/signed", content=body, headers=headers).status_code == 200
    replay = client.post("/signed", content=body, headers=headers)
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "REPLAYED_SIGNATURE_NONCE"


def test_request_signing_rejects_invalid_signature() -> None:
    app = FastAPI()
    register_request_signing_middleware(
        app,
        RequestSigningRule(),
        resolve_secret=lambda _: "super-secret",
        now_provider=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    @app.post("/signed")
    def signed(payload: dict[str, int]) -> dict[str, int]:
        return {"ok": payload["value"]}

    client = TestClient(app)
    body = b'{"value":3}'
    bad_headers = {
        "x-signature": "bad",
        "x-signature-timestamp": str(int(datetime(2026, 1, 1, 12, 0, tzinfo=UTC).timestamp())),
        "x-signature-nonce": "n3",
        "x-signature-key-id": "default",
    }
    response = client.post("/signed", content=body, headers=bad_headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_REQUEST_SIGNATURE"

