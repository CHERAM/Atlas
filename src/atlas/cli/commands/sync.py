"""Implementation of `atlas sync`."""

from __future__ import annotations

import typer

from atlas.git.errors import RepoError
from atlas.git.service import RepoService


def sync_command(
    name: str | None = typer.Option(
        None, "--name", "-n", help="Optionally sync a single repository by name."
    ),
) -> None:
    """Sync registered repositories."""
    try:
        service = RepoService()
        results = service.sync(name=name)
    except RepoError as exc:
        raise typer.BadParameter(str(exc)) from exc

    if not results:
        typer.echo("No repositories to sync.")
        return

    failed = False
    for result in results:
        status = "OK" if result.ok else "FAIL"
        commit = result.commit[:12] if result.commit else "-"
        typer.echo(f"[{status}] {result.repo.name}\t{result.action}\t{commit}\t{result.message}")
        failed = failed or (not result.ok)

    if failed:
        raise typer.Exit(code=1)
