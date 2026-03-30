"""EitohForge command line entrypoint."""

from importlib.metadata import PackageNotFoundError, version as distribution_version

import typer

from eitohforge_cli.commands.create import create_app
from eitohforge_cli.commands.db import db_app
from eitohforge_cli.commands.dev import dev_app


app = typer.Typer(
    help="EitohForge CLI for generating and operating enterprise FastAPI backends.",
    no_args_is_help=True,
)
app.add_typer(create_app, name="create")
app.add_typer(db_app, name="db")
app.add_typer(dev_app, name="dev")


@app.callback()
def root() -> None:
    """EitohForge root command group."""


@app.command("version")
def version() -> None:
    """Show current CLI version."""
    try:
        v = distribution_version("eitohforge")
    except PackageNotFoundError:
        v = "0.0.0-dev"
    typer.echo(f"eitohforge {v}")


def run() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    run()

