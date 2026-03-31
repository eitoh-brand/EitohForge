"""HTTP tests for inbound webhook router."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from eitohforge_sdk.infrastructure.webhooks.inbound import register_inbound_webhook_router


def test_inbound_webhook_plain_hmac() -> None:
    app = FastAPI()
    register_inbound_webhook_router(
        app,
        path="/hooks/in",
        secret="shh",
        use_timestamp_canonical=False,
    )
    client = TestClient(app)
    import hashlib
    import hmac

    body = b'{"x":1}'
    sig = hmac.new(b"shh", body, hashlib.sha256).hexdigest()
    res = client.post("/hooks/in", content=body, headers={"X-Webhook-Signature": sig})
    assert res.status_code == 200
    assert res.json().get("success") is True


def test_inbound_webhook_rejects_bad_sig() -> None:
    app = FastAPI()
    register_inbound_webhook_router(
        app,
        path="/hooks/in",
        secret="shh",
        use_timestamp_canonical=False,
    )
    client = TestClient(app)
    res = client.post("/hooks/in", content=b"{}", headers={"X-Webhook-Signature": "bad"})
    assert res.status_code == 401
