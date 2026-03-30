from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from eitohforge_sdk.core.idempotency import IdempotencyRule, register_idempotency_middleware


def test_idempotency_replays_same_write_request() -> None:
    app = FastAPI()
    register_idempotency_middleware(app, IdempotencyRule())
    counter = {"value": 0}

    @app.post("/payments")
    def create_payment(payload: dict[str, int]) -> dict[str, int]:
        counter["value"] += 1
        return {"counter": counter["value"], "amount": payload["amount"]}

    client = TestClient(app)
    headers = {"idempotency-key": "abc-123"}
    first = client.post("/payments", json={"amount": 10}, headers=headers)
    second = client.post("/payments", json={"amount": 10}, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == {"counter": 1, "amount": 10}
    assert second.json() == {"counter": 1, "amount": 10}
    assert second.headers.get("X-Idempotent-Replay") == "true"
    assert counter["value"] == 1


def test_idempotency_key_reuse_with_different_payload_returns_conflict() -> None:
    app = FastAPI()
    register_idempotency_middleware(app, IdempotencyRule())

    @app.post("/orders")
    def create_order(payload: dict[str, int]) -> dict[str, int]:
        return {"amount": payload["amount"]}

    client = TestClient(app)
    headers = {"idempotency-key": "order-key"}
    first = client.post("/orders", json={"amount": 50}, headers=headers)
    second = client.post("/orders", json={"amount": 75}, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_idempotency_applies_only_to_write_methods() -> None:
    app = FastAPI()
    register_idempotency_middleware(app, IdempotencyRule())
    counter = {"value": 0}

    @app.get("/read")
    def read() -> dict[str, int]:
        counter["value"] += 1
        return {"counter": counter["value"]}

    client = TestClient(app)
    headers = {"idempotency-key": "same-key"}
    first = client.get("/read", headers=headers)
    second = client.get("/read", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["counter"] == 2

