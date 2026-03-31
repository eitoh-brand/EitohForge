"""Create command group."""

from pathlib import Path
import re
from typing import Literal

import typer

from eitohforge_cli.template_parts.crud_templates import build_crud_context, render_crud_project_templates
from eitohforge_cli.template_parts.generator_templates import (
    build_generator_context,
    render_module_templates,
    render_plugin_templates,
    render_provider_templates,
)
from eitohforge_cli.templates import build_context, render_project


create_app = typer.Typer(help="Generate scaffolded resources.")


def _validate_project_name(project_name: str) -> None:
    pattern = r"^[A-Za-z][A-Za-z0-9_-]*$"
    if re.fullmatch(pattern, project_name) is None:
        raise typer.BadParameter(
            "Project name must start with a letter and contain only letters, numbers, '-' or '_'."
        )


def _validate_module_name(module_name: str) -> None:
    pattern = r"^[A-Za-z][A-Za-z0-9_]*$"
    if re.fullmatch(pattern, module_name) is None:
        raise typer.BadParameter(
            "Module name must start with a letter and contain only letters, numbers, or '_'."
        )


@create_app.command("project")
def create_project(
    project_name: str = typer.Argument(..., help="Name of the generated project (used for package/module folder names)."),
    path: Path = typer.Option(Path("."), "--path", help="Target parent directory."),
    mode: Literal["sdk", "standalone"] = typer.Option(
        "sdk",
        "--mode",
        help="Scaffold mode: 'sdk' (SDK-first) or 'standalone' (self-contained).",
    ),
    profile: Literal["standard", "minimal"] = typer.Option(
        "standard",
        "--profile",
        help="Env defaults: 'standard' (most platform features on) or 'minimal' (opt-in via EITOHFORGE_*).",
    ),
) -> None:
    """Create a new layered backend project scaffold.

    This renders the full project structure (app/, modules/, infra/, settings/, etc.)
    with feature flags derived from the selected `profile`.
    """
    _validate_project_name(project_name)
    target_parent = path.resolve()
    if not target_parent.exists():
        raise typer.BadParameter(f"Target path does not exist: {target_parent}")

    project_dir = target_parent / project_name
    if project_dir.exists():
        raise typer.BadParameter(f"Directory already exists: {project_dir}")

    project_dir.mkdir(parents=True, exist_ok=False)
    render_project(project_dir, build_context(project_name, forge_profile=profile), mode=mode)
    typer.echo(f"Project scaffold created at: {project_dir} (mode={mode}, profile={profile})")


@create_app.command("crud")
def create_crud_module(
    module_name: str = typer.Argument(..., help="CRUD module name (e.g. `orders`, `billing`, `support_tickets`)."),
    path: Path = typer.Option(Path("."), "--path", help="Target project directory."),
) -> None:
    """Generate a CRUD module scaffold inside an existing project.

    The command expects the target directory to look like a previously generated
    project (it must contain an `app/` folder).
    """
    _validate_module_name(module_name)
    context = build_crud_context(module_name)
    project_dir = path.resolve()
    if not project_dir.exists():
        raise typer.BadParameter(f"Project path does not exist: {project_dir}")

    app_dir = project_dir / "app"
    if not app_dir.exists():
        raise typer.BadParameter(f"Not a generated project (missing app/): {project_dir}")

    modules_dir = app_dir / "modules" / context.module_name
    if modules_dir.exists():
        raise typer.BadParameter(f"CRUD module already exists: {modules_dir}")
    for relative_path, content in render_crud_project_templates(context).items():
        destination = project_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    typer.echo(f"CRUD module scaffold created at: {modules_dir}")


@create_app.command("pseudocode")
def create_pseudocode(
    path: Path = typer.Option(Path("."), "--path", help="Target project directory."),
    filename: str = typer.Option(
        "architecture-pseudocode.md", "--filename", help="Output markdown filename."
    ),
) -> None:
    """Generate a practical architecture pseudocode guide for implementation phases."""
    project_dir = path.resolve()
    if not project_dir.exists():
        raise typer.BadParameter(f"Project path does not exist: {project_dir}")
    docs_dir = project_dir / "docs" / "pseudocode"
    docs_dir.mkdir(parents=True, exist_ok=True)
    output_path = docs_dir / filename
    content = """# EitohForge Implementation Pseudocode (Clean Architecture First)

## Phase 1: Run REST API with SDK standard profile

```text
create project (sdk, standard)
configure database + jwt secret
build app using build_forge_app(ForgeAppBuildConfig(...))
expose /health /ready /status /sdk/capabilities
open /docs (Swagger) or /redoc; use GET /openapi.json for schema
run uvicorn and verify baseline routes
```

## Phase 2: Enable baseline security and auth

```text
set EITOHFORGE_AUTH_JWT_ENABLED=true
set EITOHFORGE_RUNTIME_ENFORCE_HTTPS_REDIRECT=true
set EITOHFORGE_SECURITY_HARDENING_ENABLED=true
set EITOHFORGE_REQUEST_SIGNING_ENABLED=true (if external API trust boundary requires HMAC)
```

## Phase 3: Environment progression (local -> dev -> staging -> prod/UAT)

```text
local: sqlite/in-memory + relaxed features
dev/staging: postgres/redis + production-like integrations
prod: strict cors/https/signing/tenant/rate-limit + full observability
uat: operational target mapped to app_env=staging unless custom app_env enum is introduced in SDK
```

## Phase 4: Realtime + sockets

```text
set EITOHFORGE_REALTIME_ENABLED=true
set EITOHFORGE_REALTIME_REQUIRE_ACCESS_JWT=true
if multiple workers:
  set EITOHFORGE_REALTIME_REDIS_URL=redis://...
verify websocket /realtime/ws handshake + auth
```

## Phase 5: Notifications, jobs, webhooks

```text
wire notification gateway adapters (email/sms/push)
define webhook endpoints + signing secret
run background jobs for retries/fan-out
```

## Phase 6: Multi-DB and search

```text
set EITOHFORGE_DB_ANALYTICS_ENABLED=true when analytics db is needed
set EITOHFORGE_DB_SEARCH_ENABLED=true when dedicated search store is needed
route repository/read models based on workload
```

## Phase 7: Multi-app / multi-port local topology

```text
define services in forge.dev.json
service api -> app.main:app :8000
service worker-api -> worker_app.main:app :8100
run eitohforge dev
```

## Phase 8: Transport hardening (TLS/certificate pinning)

```text
terminate TLS at gateway/ingress with managed certificates
enable upstream cert validation in API clients
for mobile/edge clients: pin server cert/public key at client layer
document rotation policy and fallback
```
"""
    output_path.write_text(content, encoding="utf-8")
    typer.echo(f"Pseudocode guide generated at: {output_path}")


def _require_app_dir(project_dir: Path) -> Path:
    app_dir = project_dir / "app"
    if not app_dir.exists():
        raise typer.BadParameter(f"Not a generated project (missing app/): {project_dir}")
    return app_dir


@create_app.command("module")
def create_module(
    module_name: str = typer.Argument(..., help="Domain module name (snake_case), e.g. invoicing."),
    path: Path = typer.Option(Path("."), "--path", help="Target project directory."),
) -> None:
    """Generate a domain module (router + schema) under ``app/modules/<name>/``."""
    _validate_module_name(module_name)
    project_dir = path.resolve()
    if not project_dir.exists():
        raise typer.BadParameter(f"Project path does not exist: {project_dir}")
    _require_app_dir(project_dir)
    ctx = build_generator_context(module_name)
    modules_root = project_dir / "app" / "modules" / ctx.name
    if modules_root.exists():
        raise typer.BadParameter(f"Module already exists: {modules_root}")
    for relative_path, content in render_module_templates(ctx).items():
        destination = project_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    typer.echo(f"Module scaffold created at: {modules_root}")


@create_app.command("provider")
def create_provider(
    provider_name: str = typer.Argument(..., help="Provider name (snake_case), e.g. billing_gateway."),
    path: Path = typer.Option(Path("."), "--path", help="Target project directory."),
) -> None:
    """Scaffold an infrastructure provider stub under ``app/infrastructure/providers/``."""
    _validate_module_name(provider_name)
    project_dir = path.resolve()
    if not project_dir.exists():
        raise typer.BadParameter(f"Project path does not exist: {project_dir}")
    app_dir = _require_app_dir(project_dir)
    ctx = build_generator_context(provider_name)
    providers_dir = app_dir / "infrastructure" / "providers"
    target_file = providers_dir / f"{ctx.name}.py"
    if target_file.exists():
        raise typer.BadParameter(f"Provider already exists: {target_file}")
    for relative_path, content in render_provider_templates(ctx).items():
        destination = project_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    typer.echo(f"Provider scaffold created at: {target_file}")


@create_app.command("plugin")
def create_plugin(
    plugin_name: str = typer.Argument(..., help="Plugin name (snake_case), e.g. audit_sidebar."),
    path: Path = typer.Option(Path("."), "--path", help="Target project directory."),
) -> None:
    """Generate a Forge plugin package under ``app/plugins/<name>/`` (routes + registry hooks)."""
    _validate_module_name(plugin_name)
    project_dir = path.resolve()
    if not project_dir.exists():
        raise typer.BadParameter(f"Project path does not exist: {project_dir}")
    _require_app_dir(project_dir)
    ctx = build_generator_context(plugin_name)
    plugin_root = project_dir / "app" / "plugins" / ctx.name
    if plugin_root.exists():
        raise typer.BadParameter(f"Plugin already exists: {plugin_root}")
    for relative_path, content in render_plugin_templates(ctx).items():
        destination = project_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    typer.echo(f"Plugin scaffold created at: {plugin_root}")

