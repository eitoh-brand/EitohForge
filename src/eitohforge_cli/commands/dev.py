"""Multi-service local development (several uvicorn processes, one CLI)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import typer

FORGE_DEV_SCHEMA_VERSION = 1

dev_app = typer.Typer(
    help="Run multiple FastAPI apps from forge.dev.json (multi-port local dev).",
    invoke_without_command=True,
)


def _parse_services(data: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    if data.get("schema_version") not in (None, FORGE_DEV_SCHEMA_VERSION):
        raise ValueError(
            f"Unsupported forge.dev.json schema_version {data.get('schema_version')!r}; "
            f"expected {FORGE_DEV_SCHEMA_VERSION} or omit."
        )
    services = data.get("services")
    if not isinstance(services, list) or not services:
        raise ValueError("forge.dev.json must contain a non-empty 'services' array.")
    default_host = str(data.get("default_host", "127.0.0.1"))
    return services, default_host


def _resolve_service_run(
    *,
    project_root: Path,
    index: int,
    raw: dict[str, Any],
    default_host: str,
) -> tuple[str, list[str], str, Path]:
    """Return (label, uvicorn_cmd, display_url, cwd)."""
    name = str(raw.get("name", f"service-{index}"))
    module = raw.get("module")
    if not module or not isinstance(module, str) or ":" not in module:
        raise ValueError(f"Service {name!r} must set 'module' to 'package.module:app'.")
    host = str(raw.get("host", default_host))
    port = int(raw.get("port", 8000 + index))
    env_block = raw.get("env")
    if env_block is not None and not isinstance(env_block, dict):
        raise ValueError(f"Service {name!r}: 'env' must be an object of string keys to string values.")
    cwd = project_root
    wd = raw.get("working_directory")
    if wd:
        cwd = (project_root / str(wd)).resolve()
        if not cwd.is_dir():
            raise ValueError(f"Service {name!r}: working_directory {cwd} is not a directory.")
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        module,
        "--host",
        host,
        "--port",
        str(port),
    ]
    url = f"http://{host}:{port}"
    return name, cmd, f"{url}  ({module})", cwd


def _start_processes(
    *,
    project_root: Path,
    services: list[dict[str, Any]],
    default_host: str,
) -> list[subprocess.Popen[bytes]]:
    processes: list[subprocess.Popen[bytes]] = []
    for index, raw in enumerate(services):
        if not isinstance(raw, dict):
            raise ValueError("Each entry in 'services' must be an object.")
        name, cmd, display, cwd = _resolve_service_run(
            project_root=project_root, index=index, raw=raw, default_host=default_host
        )
        env = os.environ.copy()
        extra = raw.get("env")
        if isinstance(extra, dict):
            for key, value in extra.items():
                env[str(key)] = str(value)
        typer.echo(f"[eitohforge dev] {name} -> {display}")
        processes.append(subprocess.Popen(cmd, cwd=str(cwd), env=env))
    return processes


@dev_app.callback(invoke_without_command=True)
def dev_root(
    ctx: typer.Context,
    path: Path = typer.Option(Path("."), "--path", help="Directory containing forge.dev.json."),
    file: str = typer.Option("forge.dev.json", "--file", "-f", help="Manifest file name."),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    project_root = path.resolve()
    config_path = project_root / file
    if not config_path.is_file():
        typer.secho(f"Missing {config_path}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        typer.secho(f"Invalid JSON in {config_path}: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    if not isinstance(data, dict):
        typer.secho("forge.dev.json must be a JSON object.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    try:
        services, default_host = _parse_services(data)
        processes = _start_processes(project_root=project_root, services=services, default_host=default_host)
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    try:
        for proc in processes:
            proc.wait()
    except KeyboardInterrupt:
        typer.echo("\n[eitohforge dev] stopping…")
        for proc in processes:
            proc.terminate()
        for proc in processes:
            proc.wait(timeout=5)


@dev_app.command("validate")
def dev_validate(
    path: Path = typer.Option(Path("."), "--path"),
    file: str = typer.Option("forge.dev.json", "--file", "-f"),
) -> None:
    """Check forge.dev.json without starting servers."""
    project_root = path.resolve()
    config_path = project_root / file
    if not config_path.is_file():
        typer.secho(f"Missing {config_path}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        typer.secho(f"Invalid JSON in {config_path}: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    if not isinstance(data, dict):
        typer.secho("forge.dev.json must be a JSON object.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    try:
        services, default_host = _parse_services(data)
        for index, raw in enumerate(services):
            if not isinstance(raw, dict):
                raise ValueError("Each entry in 'services' must be an object.")
            _resolve_service_run(project_root=project_root, index=index, raw=raw, default_host=default_host)
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    typer.secho(f"OK: {len(services)} service(s), default_host={default_host!r}", fg=typer.colors.GREEN)
