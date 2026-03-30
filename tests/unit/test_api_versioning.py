from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from eitohforge_sdk.core.api_versioning import ApiVersion, register_versioned_routers


def _health_router() -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return router


def test_register_versioned_routers_exposes_v1_and_v2_paths() -> None:
    app = FastAPI()
    register_versioned_routers(
        app,
        {
            ApiVersion.V1: (_health_router(),),
            ApiVersion.V2: (_health_router(),),
        },
    )
    client = TestClient(app)
    assert client.get("/v1/health").status_code == 200
    assert client.get("/v2/health").status_code == 200

