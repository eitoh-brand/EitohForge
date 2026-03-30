"""Run example project test suites in isolation (no editable install required for examples)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]


def _run_example_tests(example_dir: str) -> None:
    ex_root = _ROOT / "examples" / example_dir
    if not ex_root.is_dir():
        pytest.skip(f"Missing example directory: {ex_root}")
    path_parts = [str(ex_root)]
    if existing := os.environ.get("PYTHONPATH"):
        path_parts.append(existing)
    env = os.environ | {"PYTHONPATH": os.pathsep.join(path_parts)}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(ex_root / "tests"), "-q"],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"{example_dir} tests failed:\n{result.stdout}\n{result.stderr}"


def test_example_minimal_smoke() -> None:
    _run_example_tests("example-minimal")


def test_example_enterprise_smoke() -> None:
    _run_example_tests("example-enterprise")
