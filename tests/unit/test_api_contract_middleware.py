from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from eitohforge_sdk.core.api_contract_middleware import ApiContractRule, register_api_contract_middleware


def test_api_contract_middleware_accepts_envelope_success() -> None:
    app = FastAPI()
    register_api_contract_middleware(app, rule=ApiContractRule(enabled=True))

    @app.get("/ok")
    def ok() -> dict[str, object]:
        return {"success": True, "data": {"x": 1}}

    client = TestClient(app)
    r = client.get("/ok")
    assert r.status_code == 200
    assert r.json()["success"] is True


def test_api_contract_middleware_rejects_missing_success() -> None:
    app = FastAPI()
    register_api_contract_middleware(app, rule=ApiContractRule(enabled=True))

    @app.get("/bad")
    def bad() -> dict[str, str]:
        return {"foo": "bar"}

    client = TestClient(app)
    r = client.get("/bad")
    assert r.status_code == 500
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_API_ENVELOPE"


def test_api_contract_skips_excluded_paths() -> None:
    app = FastAPI()
    register_api_contract_middleware(app, rule=ApiContractRule(enabled=True))

    @app.get("/docs/extra")
    def raw() -> dict[str, str]:
        return {"not": "envelope"}

    client = TestClient(app)
    r = client.get("/docs/extra")
    assert r.status_code == 200
