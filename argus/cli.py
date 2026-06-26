"""Argus CLI entry point."""

import typer

from argus import __version__

app = typer.Typer(
    name="argus",
    help="Argus Environmental Intelligence Platform.",
    add_completion=False,
    no_args_is_help=True,
)


@app.callback()
def _main() -> None:
    """Argus Environmental Intelligence Platform."""


@app.command()
def version() -> None:
    """Print the Argus version and exit."""
    typer.echo(f"argus {__version__}")


if __name__ == "__main__":
    app()
