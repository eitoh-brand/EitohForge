"""Verify wheel and sdist outputs are reproducible."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python scripts/verify_reproducible_build.py <build_dir_a> <build_dir_b>")

    first = Path(sys.argv[1]).resolve()
    second = Path(sys.argv[2]).resolve()

    first_map = _artifact_hashes(first)
    second_map = _artifact_hashes(second)

    if set(first_map) != set(second_map):
        raise SystemExit(
            f"Artifact file set mismatch. A={sorted(first_map.keys())} B={sorted(second_map.keys())}"
        )

    mismatches = [
        filename for filename in sorted(first_map.keys()) if first_map[filename] != second_map[filename]
    ]
    if mismatches:
        raise SystemExit(f"Non-reproducible artifacts detected: {mismatches}")

    print(f"Reproducible build verified for {len(first_map)} artifacts.")
    return 0


def _artifact_hashes(path: Path) -> dict[str, str]:
    if not path.exists():
        raise SystemExit(f"Build directory not found: {path}")
    files = sorted(file for file in path.iterdir() if file.is_file() and file.suffix in {".whl", ".gz"})
    if not files:
        raise SystemExit(f"No wheel/sdist artifacts found in: {path}")
    return {file.name: _sha256(file) for file in files}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(8192)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
