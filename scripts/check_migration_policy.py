"""Migration safety and structure checks for CI."""

from __future__ import annotations

from pathlib import Path


DESTRUCTIVE_ALLOW_MARKER = "MIGRATION_APPROVED_DESTRUCTIVE"
DESTRUCTIVE_PATTERNS = (
    "op.drop_table(",
    "op.drop_column(",
    "drop table ",
    "drop column ",
    "truncate table ",
)


def _iter_migration_projects(root: Path) -> list[Path]:
    return [ini.parent for ini in root.rglob("alembic.ini")]


def _check_migration_scaffold(project_path: Path) -> list[str]:
    errors: list[str] = []
    required_paths = (
        project_path / "migrations" / "env.py",
        project_path / "migrations" / "versions",
    )
    for required_path in required_paths:
        if not required_path.exists():
            errors.append(f"Missing required migration path: {required_path}")
    return errors


def _check_destructive_migrations(root: Path) -> list[str]:
    errors: list[str] = []
    for migration_file in root.rglob("migrations/versions/*.py"):
        content = migration_file.read_text(encoding="utf-8").lower()
        is_destructive = any(pattern in content for pattern in DESTRUCTIVE_PATTERNS)
        if not is_destructive:
            continue
        if DESTRUCTIVE_ALLOW_MARKER.lower() not in content:
            errors.append(
                f"Destructive migration detected without '{DESTRUCTIVE_ALLOW_MARKER}': {migration_file}"
            )
    return errors


def main() -> int:
    root = Path.cwd()
    errors: list[str] = []

    for project_path in _iter_migration_projects(root):
        errors.extend(_check_migration_scaffold(project_path))

    errors.extend(_check_destructive_migrations(root))

    if errors:
        print("Migration policy check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Migration policy check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

