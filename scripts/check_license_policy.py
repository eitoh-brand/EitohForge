"""Enforce license policy from generated compliance/licenses.json."""

from __future__ import annotations

import json
from pathlib import Path


BLOCKED_LICENSE_TOKENS = (
    "gpl",
    "agpl",
    "lgpl",
    "sspl",
)


def main() -> int:
    report_path = Path("compliance/licenses.json")
    if not report_path.exists():
        raise SystemExit("Missing license report at compliance/licenses.json.")

    data = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("Unexpected licenses report format: expected list.")

    unknown: list[str] = []
    blocked: list[str] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("Name", "unknown"))
        license_name = str(item.get("License", "UNKNOWN"))
        normalized = license_name.strip().lower()
        if normalized in {"", "unknown"}:
            unknown.append(name)
            continue
        if any(token in normalized for token in BLOCKED_LICENSE_TOKENS):
            blocked.append(f"{name} ({license_name})")

    if unknown:
        raise SystemExit(f"Unknown dependency license detected: {unknown}")
    if blocked:
        raise SystemExit(f"Blocked dependency license detected: {blocked}")

    print("License policy check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
