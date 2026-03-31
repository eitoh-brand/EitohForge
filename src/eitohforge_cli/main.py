"""EitohForge command line entrypoint."""

from importlib.metadata import PackageNotFoundError, version as distribution_version

import typer

from eitohforge_cli.commands.config import config_app
from eitohforge_cli.commands.create import create_app
from eitohforge_cli.commands.db import db_app
from eitohforge_cli.commands.dev import dev_app
from eitohforge_cli.commands.doctor import doctor_app
from eitohforge_cli.commands.docs import docs_app
from eitohforge_cli.commands.feature_flags import feature_flags_app
from eitohforge_cli.commands.ops import ops_app


app = typer.Typer(
    help="EitohForge CLI for generating and operating enterprise FastAPI backends.",
    no_args_is_help=True,
)
app.add_typer(create_app, name="create")
app.add_typer(db_app, name="db")
app.add_typer(dev_app, name="dev")
app.add_typer(config_app, name="config")
app.add_typer(docs_app, name="docs")
app.add_typer(ops_app, name="ops")
app.add_typer(feature_flags_app, name="feature-flags")
app.add_typer(doctor_app, name="doctor")


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

