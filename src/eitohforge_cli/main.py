"""EitohForge command line entrypoint."""

import typer

from eitohforge_cli.commands.create import create_app
from eitohforge_cli.commands.db import db_app


app = typer.Typer(
    help="EitohForge CLI for generating and operating enterprise FastAPI backends.",
    no_args_is_help=True,
)
app.add_typer(create_app, name="create")
app.add_typer(db_app, name="db")


@app.callback()
def root() -> None:
    """EitohForge root command group."""


@app.command("version")
def version() -> None:
    """Show current CLI version."""
    typer.echo("eitohforge 0.1.0")


def run() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    run()

