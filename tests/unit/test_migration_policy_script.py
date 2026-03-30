from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "check_migration_policy.py"
    spec = importlib.util.spec_from_file_location("check_migration_policy", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_policy_passes_without_migration_projects(tmp_path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.chdir(tmp_path)
    assert module.main() == 0


def test_migration_policy_fails_for_destructive_migration_without_marker(
    tmp_path, monkeypatch
) -> None:
    module = _load_module()
    project = tmp_path / "svc"
    versions = project / "migrations" / "versions"
    versions.mkdir(parents=True)
    (project / "alembic.ini").write_text("[alembic]\n", encoding="utf-8")
    (project / "migrations" / "env.py").write_text("# env\n", encoding="utf-8")
    (versions / "001_drop_users.py").write_text(
        "from alembic import op\n\n\ndef upgrade():\n    op.drop_table('users')\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    assert module.main() == 1


def test_migration_policy_allows_destructive_when_marker_present(tmp_path, monkeypatch) -> None:
    module = _load_module()
    project = tmp_path / "svc"
    versions = project / "migrations" / "versions"
    versions.mkdir(parents=True)
    (project / "alembic.ini").write_text("[alembic]\n", encoding="utf-8")
    (project / "migrations" / "env.py").write_text("# env\n", encoding="utf-8")
    (versions / "001_drop_users.py").write_text(
        "from alembic import op\n"
        "# MIGRATION_APPROVED_DESTRUCTIVE\n\n"
        "def upgrade():\n    op.drop_table('users')\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    assert module.main() == 0

