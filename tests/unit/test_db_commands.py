from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from eitohforge_cli.main import app


def test_db_current_invokes_alembic_with_expected_args(monkeypatch) -> None:
    runner = CliRunner()
    called: dict[str, Any] = {}

    def fake_run_alembic(args: list[str], project_path: Path, config_path: Path | None = None) -> None:
        called["args"] = args
        called["project_path"] = project_path
        called["config_path"] = config_path

    with runner.isolated_filesystem():
        Path("svc").mkdir()
        Path("svc/alembic.ini").write_text("[alembic]\n", encoding="utf-8")
        monkeypatch.setattr("eitohforge_cli.commands.db._run_alembic", fake_run_alembic)
        result = runner.invoke(app, ["db", "current", "--path", "svc"])
        assert result.exit_code == 0
        assert called["args"] == ["current"]
        assert called["project_path"].name == "svc"
        assert called["config_path"].name == "alembic.ini"


def test_db_migrate_requires_message() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("svc").mkdir()
        Path("svc/alembic.ini").write_text("[alembic]\n", encoding="utf-8")
        result = runner.invoke(app, ["db", "migrate", "--path", "svc"])
        assert result.exit_code != 0


def test_db_init_skips_when_scaffold_exists(monkeypatch) -> None:
    runner = CliRunner()
    called = False

    def fake_run_alembic(args: list[str], project_path: Path, config_path: Path | None = None) -> None:
        nonlocal called
        _ = (args, project_path, config_path)
        called = True

    with runner.isolated_filesystem():
        Path("svc/migrations").mkdir(parents=True)
        Path("svc/alembic.ini").write_text("[alembic]\n", encoding="utf-8")
        monkeypatch.setattr("eitohforge_cli.commands.db._run_alembic", fake_run_alembic)
        result = runner.invoke(app, ["db", "init", "--path", "svc"])
        assert result.exit_code == 0
        assert "already exists" in result.stdout
        assert called is False


def test_db_upgrade_passes_revision_argument(monkeypatch) -> None:
    runner = CliRunner()
    captured: dict[str, Any] = {}

    def fake_run_alembic(args: list[str], project_path: Path, config_path: Path | None = None) -> None:
        captured["args"] = args
        captured["project_path"] = project_path
        captured["config_path"] = config_path

    with runner.isolated_filesystem():
        Path("svc").mkdir()
        Path("svc/alembic.ini").write_text("[alembic]\n", encoding="utf-8")
        monkeypatch.setattr("eitohforge_cli.commands.db._run_alembic", fake_run_alembic)
        result = runner.invoke(app, ["db", "upgrade", "--path", "svc", "--revision", "head"])
        assert result.exit_code == 0
        assert captured["args"] == ["upgrade", "head"]

