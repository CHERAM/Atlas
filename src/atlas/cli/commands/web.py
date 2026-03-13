"""Implementation of `atlas web` commands."""

from __future__ import annotations

import typer

from atlas.web.errors import WebError
from atlas.web.ingest import WebIngestionService
from atlas.web.registry import WebRegistryService


def web_add_command(
    url: str,
    kind: str = typer.Option("docs", "--kind", help="Source kind label, e.g. docs/wiki."),
    source_id: str | None = typer.Option(None, "--id", help="Optional explicit source id."),
    ingest_now: bool = typer.Option(False, "--ingest-now", help="Run one-time ingestion after add."),
) -> None:
    """Register a web source."""
    try:
        registry = WebRegistryService()
        source = registry.add_source(url=url, kind=kind, source_id=source_id)
        typer.echo(f"Added web source '{source.source_id}' ({source.url}) kind={source.kind}")
        if ingest_now:
            result = WebIngestionService().ingest_source(source.source_id)
            status = "OK" if result.ok else "FAIL"
            typer.echo(f"[ingest:{status}] {result.source_id} {result.message}")
    except WebError as exc:
        raise typer.BadParameter(str(exc)) from exc


def web_list_command() -> None:
    """List registered web sources."""
    try:
        sources = WebRegistryService().list_sources()
    except WebError as exc:
        raise typer.BadParameter(str(exc)) from exc

    if not sources:
        typer.echo("No web sources registered.")
        return

    for source in sources:
        state = "enabled" if source.enabled else "disabled"
        typer.echo(f"{source.source_id}\t{source.kind}\t{source.url}\t{state}")


def web_remove_command(source_id: str) -> None:
    """Remove registered web source."""
    try:
        removed = WebRegistryService().remove_source(source_id)
        typer.echo(f"Removed web source '{removed.source_id}' ({removed.url})")
    except WebError as exc:
        raise typer.BadParameter(str(exc)) from exc


def web_ingest_command(
    source_id: str | None = typer.Option(None, "--id", help="Source id to ingest."),
    all_sources: bool = typer.Option(False, "--all", help="Ingest all enabled web sources."),
) -> None:
    """Run one-time raw HTML ingestion for registered sources."""
    if not source_id and not all_sources:
        raise typer.BadParameter("Specify --id <source-id> or --all.")
    if source_id and all_sources:
        raise typer.BadParameter("Use either --id or --all, not both.")

    service = WebIngestionService()
    if all_sources:
        results = service.ingest_all()
    else:
        results = [service.ingest_source(source_id)]

    failed = False
    for result in results:
        status = "OK" if result.ok else "FAIL"
        out_path = str(result.html_path) if result.html_path else "-"
        typer.echo(f"[ingest:{status}] {result.source_id}\t{out_path}\t{result.message}")
        failed = failed or (not result.ok)

    if failed:
        raise typer.Exit(code=1)
