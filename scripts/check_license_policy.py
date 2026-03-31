"""Enforce license policy from generated compliance/licenses.json."""

from __future__ import annotations

import json
import re
from pathlib import Path


# License policy:
# - We block strong copyleft licenses (GPL/AGPL/SSPL).
# - We allow LGPL because it is explicitly designed to enable linking by non-(L)GPL-licensed
#   applications while preserving library freedoms.
# - Some packages declare multiple licenses (e.g. docutils "BSD; GPL; Public Domain").
#   For those, we only block if *all* declared variants are strong-copyleft.
BLOCKED_LICENSE_TOKENS = (
    "gpl",
    "agpl",
    "sspl",
)

# Transitive dependencies that sometimes report ``UNKNOWN`` in pip-licenses JSON even though the
# upstream project publishes an SPDX license (manual review; keep this list tiny).
UNKNOWN_LICENSE_ALLOWLIST: dict[str, str] = {
    # Google CRC32C extension; Apache-2.0 per PyPI metadata; pip-licenses may still show UNKNOWN.
    "google-crc32c": "Apache-2.0 (allowlisted; pip-licenses UNKNOWN)",
}

def _variant_mentions_blocked_token(variant: str, token: str) -> bool:
    """
    Return True if `variant` should be considered blocked by `token`.

    Important edge case:
    - `LGPL...` contains the substring `gpl`, but we do NOT want to treat LGPL as GPL.
    """

    if token == "gpl":
        # Block only "GPL" occurrences that are NOT part of "LGPL".
        # Negative lookbehind avoids matching the "gpl" inside "lgpl".
        return re.search(r"(?<!l)gpl", variant) is not None

    return token in variant


def _license_variants(license_name: str) -> list[str]:
    """
    Split pip-licenses license string into variants.

    Examples:
      - "BSD License; GNU General Public License (GPL); Public Domain"
      - "LGPL-3.0-only"
    """

    s = license_name.strip().lower()
    if not s:
        return []

    # pip-licenses uses strings that are often separated by ';' (and sometimes ',' / ' or ').
    parts = re.split(r"\s*;\s*|\s*,\s*|\s+or\s+", s)
    return [p.strip() for p in parts if p.strip()]


def _is_blocked_license(license_name: str) -> bool:
    variants = _license_variants(license_name)
    if not variants:
        normalized = license_name.strip().lower()
        return any(_variant_mentions_blocked_token(normalized, token) for token in BLOCKED_LICENSE_TOKENS)

    # Block only if every variant mentions a blocked token.
    return all(
        any(_variant_mentions_blocked_token(variant, token) for token in BLOCKED_LICENSE_TOKENS)
        for variant in variants
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
            if name in UNKNOWN_LICENSE_ALLOWLIST:
                continue
            unknown.append(name)
            continue
        if _is_blocked_license(license_name):
            blocked.append(f"{name} ({license_name})")

    if unknown:
        raise SystemExit(f"Unknown dependency license detected: {unknown}")
    if blocked:
        raise SystemExit(f"Blocked dependency license detected: {blocked}")

    print("License policy check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
