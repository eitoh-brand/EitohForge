"""Project sanity checks."""

from __future__ import annotations

import json
from pathlib import Path

import typer

doctor_app = typer.Typer(help="Project sanity checks for generated repositories.")


def _check_exists(path: Path, expected: str) -> tuple[bool, str]:
    if not path.exists():
        return False, f"missing: {expected}"
    return True, f"ok: {expected}"


@doctor_app.command("check")
def doctor_check(
    path: Path = typer.Option(Path("."), "--path", help="Project root path."),
    file: str = typer.Option("forge.dev.json", "--file", "-f", help="Local multi-service manifest."),
) -> None:
    """Run a quick generated-project structure validation."""
    project_root = path.resolve()
    checks = (
        (project_root / "pyproject.toml", "pyproject.toml"),
        (project_root / "app", "app/"),
        (project_root / "app" / "main.py", "app/main.py"),
        (project_root / "alembic.ini", "alembic.ini"),
        (project_root / "migrations", "migrations/"),
        (project_root / ".env.example", ".env.example"),
    )
    failures = 0
    for check_path, expected in checks:
        ok, message = _check_exists(check_path, expected)
        typer.secho(message, fg=typer.colors.GREEN if ok else typer.colors.RED)
        if not ok:
            failures += 1

    manifest_path = project_root / file
    if manifest_path.exists():
        try:
            content = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(content, dict) and isinstance(content.get("services"), list):
                typer.secho(f"ok: {file} contains services array", fg=typer.colors.GREEN)
            else:
                failures += 1
                typer.secho(f"invalid: {file} must include a services array", fg=typer.colors.RED)
        except json.JSONDecodeError:
            failures += 1
            typer.secho(f"invalid: {file} is not valid JSON", fg=typer.colors.RED)
    else:
        typer.secho(f"warn: optional {file} not found", fg=typer.colors.YELLOW)

    if failures:
        raise typer.Exit(code=1)

