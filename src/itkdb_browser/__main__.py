"""
Top-level entrypoint for the command line interface.
"""
from __future__ import annotations

import typer

import itkdb_browser

app = typer.Typer()


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(False, "--version", help="Print the current version."),
) -> None:
    """
    Manage top-level options
    """
    if version:
        typer.echo(f"itkdb-browser v{itkdb_browser.__version__}")
        raise typer.Exit()
    typer.echo("Browser goes in here")


# for generating documentation using mkdocs-click
typer_click_object = typer.main.get_command(app)

if __name__ == "__main__":
    app(prog_name="itkdb-browser")
