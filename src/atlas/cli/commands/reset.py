"""Implementation of `atlas reset`."""

from __future__ import annotations

import typer

from atlas.core.cleanup import remove_hard_reset


def reset_command(
    hard: bool = typer.Option(
        False,
        "--hard",
        help="Delete cache, .github/atlas, .atlas/books, and atlas.yaml.",
    ),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt."),
) -> None:
    """Reset the Atlas workspace by deleting all local artifacts."""
    if not hard:
        raise typer.BadParameter("Specify --hard to confirm a full reset.")

    _confirm(
        force,
        "This will delete .atlas-cache, .github/atlas, .atlas/books, and atlas.yaml. Continue?",
    )
    removed = remove_hard_reset()
    if removed:
        typer.echo("Removed: " + ", ".join(str(path) for path in removed))
    else:
        typer.echo("No Atlas workspace artifacts found to remove.")


def _confirm(force: bool, message: str, confirm_fn=typer.confirm) -> None:
    if force:
        return
    if not confirm_fn(message, default=False):
        raise typer.Exit(code=1)
