"""Create command group."""

from pathlib import Path
import re
from typing import Literal

import typer

from eitohforge_cli.template_parts.crud_templates import build_crud_context, render_crud_project_templates
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

