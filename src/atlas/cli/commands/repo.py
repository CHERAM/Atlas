"""Implementation of `atlas repo` commands."""

from __future__ import annotations

import typer

from atlas.git.errors import RepoError
from atlas.git.service import RepoService


def repo_add_command(
    git_url: str,
    branch: str = typer.Option("main", "--branch", help="Branch to track for sync."),
) -> None:
    """Register a git repository source."""
    try:
        service = RepoService()
        repo = service.add_repo(git_url=git_url, branch=branch)
        typer.echo(
            f"Added repo '{repo.name}' ({repo.url}) branch={repo.branch} path={repo.local_path}"
        )
    except RepoError as exc:
        raise typer.BadParameter(str(exc)) from exc


def repo_list_command() -> None:
    """List registered repositories."""
    try:
        service = RepoService()
        repos = service.list_repos()
    except RepoError as exc:
        raise typer.BadParameter(str(exc)) from exc

    if not repos:
        typer.echo("No repositories registered.")
        return

    for repo in repos:
        typer.echo(
            f"{repo.name}\t{repo.branch}\t{repo.local_path}\t{repo.url}\t"
            f"{'enabled' if repo.enabled else 'disabled'}"
        )


def repo_remove_command(
    name: str,
    delete_local: bool = typer.Option(
        False, "--delete-local", help="Also delete the local clone directory."
    ),
) -> None:
    """Remove a repository from Atlas manifest."""
    try:
        service = RepoService()
        removed = service.remove_repo(name=name, delete_local=delete_local)
        typer.echo(
            f"Removed repo '{removed.name}' from manifest"
            + (" and deleted local clone." if delete_local else ".")
        )
    except RepoError as exc:
        raise typer.BadParameter(str(exc)) from exc
