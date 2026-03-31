"""Runtime operations commands (health/readiness/status checks)."""

from __future__ import annotations

import json
import time
from urllib import error, request

import typer

ops_app = typer.Typer(help="Runtime endpoint checks against a base URL.")


def _http_get_json(url: str, timeout_seconds: float) -> tuple[int, str]:
    req = request.Request(url=url, method="GET")
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            status = int(response.status)
            body = response.read().decode("utf-8", errors="replace")
            return status, body
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return int(exc.code), body


def _http_get_with_timing(url: str, timeout_seconds: float) -> tuple[int, str, float]:
    start = time.perf_counter()
    status, body = _http_get_json(url, timeout_seconds)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return status, body, elapsed_ms


def _print_openapi_line(status: int, body: str) -> None:
    color = typer.colors.GREEN if status < 400 else typer.colors.RED
    typer.secho(f"[openapi] {status}", fg=color)
    if status >= 400:
        return
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        typer.echo(body[:240] + ("..." if len(body) > 240 else ""))
        return
    title = str(parsed.get("info", {}).get("title", ""))
    ver = str(parsed.get("openapi", parsed.get("swagger", "")))
    typer.echo(f"OpenAPI schema {ver} — {title or '(no title)'}")


def _print_result(label: str, status: int, body: str) -> None:
    color = typer.colors.GREEN if status < 400 else typer.colors.RED
    typer.secho(f"[{label}] {status}", fg=color)
    compact_body = body.strip()
    if not compact_body:
        return
    try:
        parsed = json.loads(compact_body)
        typer.echo(json.dumps(parsed, indent=2, sort_keys=True))
    except json.JSONDecodeError:
        typer.echo(compact_body)


@ops_app.command("check")
def check(
    base_url: str = typer.Option("http://127.0.0.1:8000", "--base-url", help="Service base URL."),
    timeout_seconds: float = typer.Option(4.0, "--timeout-seconds", help="Per-request timeout."),
) -> None:
    """Check health/readiness/status/capabilities endpoints."""
    endpoints = (
        ("health", "/health"),
        ("ready", "/ready"),
        ("status", "/status"),
        ("capabilities", "/sdk/capabilities"),
        ("openapi", "/openapi.json"),
    )
    failures = 0
    root = base_url.rstrip("/")
    for label, path in endpoints:
        status, body = _http_get_json(f"{root}{path}", timeout_seconds)
        if label == "openapi":
            _print_openapi_line(status, body)
        else:
            _print_result(label, status, body)
        if status >= 400:
            failures += 1
    if failures:
        raise typer.Exit(code=1)


@ops_app.command("smoke")
def smoke(
    base_url: str = typer.Option("http://127.0.0.1:8000", "--base-url", help="Service base URL."),
    timeout_seconds: float = typer.Option(4.0, "--timeout-seconds", help="Per-request timeout."),
    max_latency_ms: float = typer.Option(500.0, "--max-latency-ms", help="Per-endpoint latency budget."),
) -> None:
    """CI-friendly smoke check with status + latency budget validation."""
    endpoints = (
        ("health", "/health"),
        ("ready", "/ready"),
        ("status", "/status"),
        ("capabilities", "/sdk/capabilities"),
        ("openapi", "/openapi.json"),
    )
    failures = 0
    root = base_url.rstrip("/")
    for label, path in endpoints:
        status, _body, elapsed_ms = _http_get_with_timing(f"{root}{path}", timeout_seconds)
        ok = status < 400 and elapsed_ms <= max_latency_ms
        color = typer.colors.GREEN if ok else typer.colors.RED
        typer.secho(
            f"{label:12} status={status:<3} latency_ms={elapsed_ms:.1f} budget_ms={max_latency_ms:.1f}",
            fg=color,
        )
        if not ok:
            failures += 1
    if failures:
        raise typer.Exit(code=1)

