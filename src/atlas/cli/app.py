"""Typer application entrypoint for Atlas."""

from __future__ import annotations

import typer

from atlas import __version__
from atlas.cli.commands import build, context, init, repo, search, sync, web
from atlas.core.logging import configure_logging

app = typer.Typer(name="atlas", help="Atlas CLI developer knowledge system.")


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", help="Print version and exit."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
) -> None:
    """Atlas top-level CLI callback."""
    configure_logging(verbose=verbose)
    if version:
        typer.echo(__version__)
        raise typer.Exit(0)


app.command(name="init")(init.init_command)
app.command(name="sync")(sync.sync_command)
app.command(name="build")(build.build_command)
app.command(name="search")(search.search_command)
app.command(name="context")(context.context_command)

repo_app = typer.Typer(help="Manage repository sources.")
repo_app.command(name="add")(repo.repo_add_command)
repo_app.command(name="list")(repo.repo_list_command)
repo_app.command(name="remove")(repo.repo_remove_command)
app.add_typer(repo_app, name="repo")

web_app = typer.Typer(help="Manage web/doc sources.")
web_app.command(name="add")(web.web_add_command)
web_app.command(name="list")(web.web_list_command)
web_app.command(name="remove")(web.web_remove_command)
web_app.command(name="ingest")(web.web_ingest_command)
app.add_typer(web_app, name="web")
