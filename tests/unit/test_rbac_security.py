from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import pytest

from eitohforge_sdk.core.error_middleware import register_error_handlers
from eitohforge_sdk.core.security import (
    RoleDeniedError,
    SecurityPrincipal,
    parse_roles,
    rbac_required,
    require_roles,
)


def test_parse_roles_normalizes_and_filters_values() -> None:
    assert parse_roles("Admin, user , ,REPORTS") == ("admin", "user", "reports")


def test_require_roles_dependency_enforces_header_roles() -> None:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/admin")
    def admin_route(
        principal: SecurityPrincipal = Depends(require_roles("admin")),
    ) -> dict[str, str]:
        return {"actor": principal.actor_id or "unknown"}

    client = TestClient(app, raise_server_exceptions=False)
    denied = client.get("/admin", headers={"x-actor-id": "u1", "x-roles": "user"})
    assert denied.status_code == 403

    allowed = client.get("/admin", headers={"x-actor-id": "u1", "x-roles": "admin"})
    assert allowed.status_code == 200


@rbac_required("admin")
def _protected_sync(*, principal: SecurityPrincipal) -> str:
    return "ok"


def test_rbac_required_decorator_enforces_principal_roles() -> None:
    with pytest.raises(RoleDeniedError):
        _protected_sync(principal=SecurityPrincipal(actor_id="u1", roles=("user",)))

    assert _protected_sync(principal=SecurityPrincipal(actor_id="u1", roles=("admin",))) == "ok"

