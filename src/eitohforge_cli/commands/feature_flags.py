"""Feature flag endpoint inspection commands."""

from __future__ import annotations

import json
from urllib import error, request

import typer

feature_flags_app = typer.Typer(help="Inspect feature flags from a running service.")


@feature_flags_app.command("get")
def get_flags(
    base_url: str = typer.Option("http://127.0.0.1:8000", "--base-url", help="Service base URL."),
    path: str = typer.Option("/sdk/feature-flags", "--path", help="Feature flags endpoint path."),
    timeout_seconds: float = typer.Option(4.0, "--timeout-seconds", help="Request timeout."),
) -> None:
    """Fetch and print the feature flags endpoint payload."""
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    req = request.Request(url=url, method="GET")
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            status = int(response.status)
            body = response.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        status = int(exc.code)
        body = exc.read().decode("utf-8", errors="replace")
    typer.echo(f"status={status}")
    try:
        parsed = json.loads(body)
        typer.echo(json.dumps(parsed, indent=2, sort_keys=True))
    except json.JSONDecodeError:
        typer.echo(body)
    if status >= 400:
        raise typer.Exit(code=1)

