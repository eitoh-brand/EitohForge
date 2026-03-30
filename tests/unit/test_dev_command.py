from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from eitohforge_cli.main import app


def test_dev_validate_accepts_minimal_manifest(tmp_path: Path) -> None:
    manifest = {
        "schema_version": 1,
        "default_host": "127.0.0.1",
        "services": [{"name": "api", "module": "acme.main:app", "port": 8010}],
    }
    (tmp_path / "forge.dev.json").write_text(json.dumps(manifest), encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["dev", "validate", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "OK:" in result.stdout


def test_dev_validate_rejects_bad_module(tmp_path: Path) -> None:
    manifest = {"services": [{"name": "x", "module": "nocolon", "port": 8000}]}
    (tmp_path / "forge.dev.json").write_text(json.dumps(manifest), encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(app, ["dev", "validate", "--path", str(tmp_path)])
    assert result.exit_code == 1
