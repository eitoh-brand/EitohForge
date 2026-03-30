from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from eitohforge_sdk.core.security_hardening import SecurityHardeningRule, register_security_hardening_middleware


def test_security_hardening_adds_default_security_headers() -> None:
    app = FastAPI()
    register_security_hardening_middleware(app, SecurityHardeningRule())

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"status": "ok"}

    response = TestClient(app).get("/ping")
    assert response.status_code == 200
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"


def test_security_hardening_blocks_disallowed_host() -> None:
    app = FastAPI()
    register_security_hardening_middleware(app, SecurityHardeningRule(allowed_hosts=("api.local",)))

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"status": "ok"}

    response = TestClient(app).get("/ping", headers={"host": "evil.local"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "HOST_NOT_ALLOWED"


def test_security_hardening_blocks_large_request_body() -> None:
    app = FastAPI()
    register_security_hardening_middleware(app, SecurityHardeningRule(max_request_bytes=8))

    @app.post("/payload")
    def payload() -> dict[str, str]:
        return {"status": "ok"}

    response = TestClient(app).post("/payload", content="x" * 32, headers={"host": "testserver"})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_ENTITY_TOO_LARGE"
