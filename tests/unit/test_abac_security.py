from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import pytest

from eitohforge_sdk.core.abac import PolicyDeniedError, TenantMatchPolicy, abac_required, require_policies
from eitohforge_sdk.core.error_middleware import register_error_handlers
from eitohforge_sdk.core.security import SecurityPrincipal


def test_require_policies_dependency_blocks_tenant_mismatch() -> None:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/tenant/{resource_tenant_id}")
    def tenant_route(_: object = Depends(require_policies(TenantMatchPolicy()))) -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(app, raise_server_exceptions=False)

    denied = client.get("/tenant/tenant-b", headers={"x-tenant-id": "tenant-a"})
    assert denied.status_code == 403

    allowed = client.get("/tenant/tenant-a", headers={"x-tenant-id": "tenant-a"})
    assert allowed.status_code == 200


@abac_required(TenantMatchPolicy())
def _abac_sync(*, principal: SecurityPrincipal, attributes: dict[str, str]) -> str:
    return "ok"


def test_abac_required_decorator_enforces_policy() -> None:
    with pytest.raises(PolicyDeniedError):
        _abac_sync(
            principal=SecurityPrincipal(actor_id="a1", tenant_id="tenant-a", roles=("user",)),
            attributes={"resource_tenant_id": "tenant-b"},
        )

    assert (
        _abac_sync(
            principal=SecurityPrincipal(actor_id="a1", tenant_id="tenant-a", roles=("user",)),
            attributes={"resource_tenant_id": "tenant-a"},
        )
        == "ok"
    )

