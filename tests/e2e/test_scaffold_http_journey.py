"""End-to-end journeys across CLI scaffold and HTTP surface."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from eitohforge_cli.main import app as cli_app


@pytest.mark.e2e
def test_cli_scaffold_exposes_core_sdk_http_paths() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        assert runner.invoke(cli_app, ["create", "project", "svc_e2e"]).exit_code == 0
        project_root = Path("svc_e2e").resolve()
        sys.path.insert(0, str(project_root))
        try:
            main = importlib.import_module("app.main")
            client = TestClient(main.app)
            assert client.get("/health").status_code == 200
            cap = client.get("/sdk/capabilities")
            assert cap.status_code == 200
            cap_body = cap.json()
            assert "features" in cap_body
            assert cap_body["features"].get("realtime_websocket") is True
            ws_paths = {getattr(r, "path", "") for r in main.app.routes}
            assert "/realtime/ws" in ws_paths
            ff = client.get("/sdk/feature-flags")
            assert ff.status_code == 200
            assert "flags" in ff.json()
        finally:
            sys.path.pop(0)
            for name in list(sys.modules):
                if name == "app" or name.startswith("app."):
                    del sys.modules[name]
