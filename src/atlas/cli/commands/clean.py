"""Implementation of `atlas clean`."""

from __future__ import annotations

import typer

from atlas.core.cleanup import remove_cache_only


def clean_command(
    cache: bool = typer.Option(
        False,
        "--cache",
        help="Remove .atlas-cache directory only.",
    ),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt."),
) -> None:
    """Remove Atlas cache artifacts from the workspace."""
    if not cache:
        raise typer.BadParameter("Specify --cache to confirm cache cleanup.")

    _confirm(
        force,
        "This will delete .atlas-cache (repos, index, and web cache). Continue?",
    )
    removed = remove_cache_only()
    if removed:
        typer.echo("Removed: " + ", ".join(str(path) for path in removed))
    else:
        typer.echo("No cache directory found to remove.")


def _confirm(force: bool, message: str, confirm_fn=typer.confirm) -> None:
    if force:
        return
    if not confirm_fn(message, default=False):
        raise typer.Exit(code=1)
