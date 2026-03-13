"""Implementation of `atlas books` commands."""

from __future__ import annotations

import typer

from atlas.core.books import BooksError, list_templates, pull_templates


def books_list_command() -> None:
    """List available Atlas books templates."""
    try:
        templates = list_templates()
    except BooksError as exc:
        raise typer.BadParameter(str(exc)) from exc

    if not templates:
        typer.echo("No books templates found.")
        return

    for template in templates:
        typer.echo(f"{template.name}\t{template.filename}\t{template.purpose}")


def books_pull_command(
    name: str | None = typer.Option(
        None,
        "--name",
        help="Template name to copy (e.g. prompt-creation).",
    ),
    pull_all: bool = typer.Option(False, "--all", help="Copy all templates."),
    all_repos: bool = typer.Option(
        False,
        "--all-repos",
        help="Copy into .github/ for all registered local repos.",
    ),
) -> None:
    """Copy books templates into destination .github directories."""
    try:
        summary = pull_templates(name=name, pull_all=pull_all, all_repos=all_repos)
    except BooksError as exc:
        raise typer.BadParameter(str(exc)) from exc

    target_count = len(summary.target_dirs)
    copied_count = len(summary.copied_files)
    typer.echo(f"Copied {copied_count} file(s) into {target_count} target .github folder(s).")
    for path in summary.copied_files:
        typer.echo(f"- {path}")
