"""Implementation of `atlas context`."""

from __future__ import annotations

import typer

from atlas.context.service import ContextService
from atlas.core.errors import AtlasError
from atlas.search.service import SearchService
from atlas.storage.embedding import HashEmbeddingClient


def context_command(
    query: str,
    top_k: int = typer.Option(20, "--top-k", min=1, help="Maximum search results to assemble."),
    critical_k: int | None = typer.Option(
        None,
        "--critical-k",
        min=0,
        help="Number of results treated as critical. If omitted, default ranking is used.",
    ),
    repo: str | None = typer.Option(None, "--repo", help="Optional repo name filter."),
) -> None:
    """Generate AI-ready context markdown."""
    try:
        search_service = SearchService.from_workspace()
        try:
            effective_critical_k = 5 if critical_k is None else critical_k
            results = search_service.search(
                query=query,
                embedding_client=HashEmbeddingClient(),
                top_k=top_k,
                critical_k=effective_critical_k,
                repo_name=repo,
            )
        finally:
            search_service.close()

        context_service = ContextService()
        output_path = context_service.generate_from_results(
            query=query,
            results=results,
            allow_all_critical=(
                critical_k is not None and critical_k >= len(results) and len(results) > 0
            ),
        )
        typer.echo(f"Wrote context to {output_path}")
    except AtlasError as exc:
        raise typer.BadParameter(str(exc)) from exc
