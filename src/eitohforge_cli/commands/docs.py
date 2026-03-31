"""Documentation helper commands."""

from __future__ import annotations

from typing import Literal

import typer

docs_app = typer.Typer(help="Documentation discovery helpers.")

_DOC_TOPICS: dict[str, tuple[str, str]] = {
    "readme": ("README", "README.md"),
    "usage": ("Complete usage guide", "docs/guides/usage-complete.md"),
    "realtime": ("Realtime websocket guide", "docs/guides/realtime-websocket.md"),
    "profiles": ("Scaffold profiles guide", "docs/guides/forge-profiles.md"),
    "cookbook": ("Cookbook", "docs/guides/cookbook.md"),
    "runbook": ("Operations runbook", "docs/guides/operations-runbook.md"),
    "architecture": ("Architecture blueprint", "secure_backend_sdk_architecture.md"),
}


@docs_app.command("list")
def docs_list() -> None:
    """List core documentation entry points."""
    for key, (title, path) in _DOC_TOPICS.items():
        typer.echo(f"{key:<12} {title:<30} {path}")


@docs_app.command("path")
def docs_path(
    topic: Literal["readme", "usage", "realtime", "profiles", "cookbook", "runbook", "architecture"] = typer.Argument(
        ..., help="Documentation topic key."
    ),
) -> None:
    """Print the canonical path for one docs topic."""
    title, path = _DOC_TOPICS[topic]
    typer.echo(f"{title}: {path}")
