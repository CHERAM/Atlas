"""Implementation of `atlas search`."""

from __future__ import annotations

import typer

from atlas.core.errors import AtlasError
from atlas.search.formatter import format_search_results
from atlas.search.service import SearchService
from atlas.storage.embedding import HashEmbeddingClient


def search_command(
    query: str,
    top_k: int = typer.Option(20, "--top-k", min=1, help="Maximum number of results."),
    critical_k: int = typer.Option(
        5, "--critical-k", min=0, help="Number of results to mark as critical."
    ),
    repo: str | None = typer.Option(None, "--repo", help="Optional repo name filter."),
) -> None:
    """Search the Atlas knowledge base."""
    try:
        service = SearchService.from_workspace()
        try:
            results = service.search(
                query=query,
                embedding_client=HashEmbeddingClient(),
                top_k=top_k,
                critical_k=critical_k,
                repo_name=repo,
            )
            typer.echo(format_search_results(results))
        finally:
            service.close()
    except AtlasError as exc:
        raise typer.BadParameter(str(exc)) from exc
