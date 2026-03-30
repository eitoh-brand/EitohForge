"""Contract tests: stable JSON shapes for SDK endpoints and error envelopes."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from eitohforge_sdk.core.capabilities import register_capabilities_endpoint
from eitohforge_sdk.core.config import AppSettings
from eitohforge_sdk.core.error_middleware import register_error_handlers
from eitohforge_sdk.core.error_registry import build_default_error_registry
from eitohforge_sdk.core.validation.errors import ValidationFailedError, ValidationIssue, ValidationResult


@pytest.mark.contract
def test_capabilities_endpoint_contract_shape() -> None:
    app = FastAPI()
    register_capabilities_endpoint(app, settings_provider=lambda: AppSettings())
    response = TestClient(app).get("/sdk/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body.get("app_name")
    assert body.get("app_env")
    assert isinstance(body.get("api_versions"), list)
    features = body.get("features")
    assert isinstance(features, dict)
    assert "rate_limit" in features
    assert "security_hardening" in features
    assert "realtime_websocket" in features
    assert isinstance(body.get("realtime"), dict)
    assert isinstance(body.get("auth"), dict)
    assert isinstance(body.get("deployment"), dict)
    assert isinstance(body.get("runtime"), dict)
    catalog = body.get("sdk_feature_catalog")
    assert isinstance(catalog, list)
    meta = body.get("sdk_feature_catalog_meta")
    assert isinstance(meta, dict)
    assert meta.get("feature_area_count") == len(catalog)


@pytest.mark.contract
def test_error_envelope_contract_for_validation() -> None:
    app = FastAPI()
    register_error_handlers(app, build_default_error_registry())

    @app.get("/bad")
    def bad() -> None:
        raise ValidationFailedError(
            ValidationResult(issues=(ValidationIssue(code="X", message="y", field="z"),))
        )

    response = TestClient(app, raise_server_exceptions=False).get("/bad")
    assert response.status_code == 422
    payload = response.json()
    assert payload.get("success") is False
    err = payload.get("error")
    assert isinstance(err, dict)
    assert err.get("code") == "VALIDATION_FAILED"
    assert isinstance(err.get("details"), list)
