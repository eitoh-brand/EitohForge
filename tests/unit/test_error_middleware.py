from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from eitohforge_sdk.core.error_middleware import register_error_handlers
from eitohforge_sdk.core.validation.errors import ValidationFailedError, ValidationIssue, ValidationResult


def test_error_middleware_maps_validation_error() -> None:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/fail")
    def fail() -> None:
        raise ValidationFailedError(
            ValidationResult(issues=(ValidationIssue(code="BAD_INPUT", message="bad", field="name"),))
        )

    response = TestClient(app, raise_server_exceptions=False).get("/fail")
    assert response.status_code == 422
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "VALIDATION_FAILED"
    assert payload["error"]["details"][0]["code"] == "BAD_INPUT"


def test_error_middleware_maps_unexpected_error() -> None:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("unexpected")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")
    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "INTERNAL_SERVER_ERROR"

