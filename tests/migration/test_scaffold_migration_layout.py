"""Migration layout and policy checks for generated projects."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from eitohforge_cli.main import app as cli_app


@pytest.mark.migration
def test_generated_project_includes_alembic_skeleton() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        assert runner.invoke(cli_app, ["create", "project", "svc_mig"]).exit_code == 0
        root = Path("svc_mig")
        assert (root / "alembic.ini").is_file()
        assert (root / "migrations" / "env.py").is_file()
        assert (root / "migrations" / "script.py.mako").is_file()
        env_src = (root / "migrations" / "env.py").read_text(encoding="utf-8")
        assert "run_migrations_online" in env_src
        assert "target_metadata" in env_src
