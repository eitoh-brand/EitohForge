"""Validate pyproject packaging metadata and entrypoints."""

from __future__ import annotations

from pathlib import Path
import tomllib


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    pyproject_path = root / "pyproject.toml"
    payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    project = payload.get("project", {})
    _require(project, "name")
    _require(project, "version")
    _require(project, "requires-python")
    _require(project, "dependencies")

    scripts = project.get("scripts", {})
    if scripts.get("eitohforge") != "eitohforge_cli.main:run":
        raise SystemExit("Expected `project.scripts.eitohforge = 'eitohforge_cli.main:run'`.")

    wheel_packages = (
        payload.get("tool", {})
        .get("hatch", {})
        .get("build", {})
        .get("targets", {})
        .get("wheel", {})
        .get("packages", [])
    )
    expected_packages = {"src/eitohforge_cli", "src/eitohforge_sdk"}
    if set(wheel_packages) != expected_packages:
        raise SystemExit(f"Wheel packages mismatch. Expected {sorted(expected_packages)}, got {wheel_packages}.")

    for package in expected_packages:
        package_path = root / package
        if not package_path.exists():
            raise SystemExit(f"Missing package path required for wheel build: {package}")
    print("Packaging metadata validation passed.")
    return 0


def _require(mapping: dict[str, object], key: str) -> None:
    value = mapping.get(key)
    if value is None or value == "":
        raise SystemExit(f"Missing required pyproject field: project.{key}")


if __name__ == "__main__":
    raise SystemExit(main())
