from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from eitohforge_cli.main import app as cli_app


def test_create_project_minimal_profile_env_example() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        assert runner.invoke(cli_app, ["create", "project", "svc_min", "--profile", "minimal"]).exit_code == 0
        text = Path("svc_min/.env.example").read_text(encoding="utf-8")
        assert "EITOHFORGE_REALTIME_ENABLED=false" in text
        assert "EITOHFORGE_TENANT_ENABLED=false" in text
        assert "EITOHFORGE_RATE_LIMIT_ENABLED=false" in text
