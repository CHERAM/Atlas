"""Implementation of `atlas build`."""

from __future__ import annotations

import typer

from atlas.chunking.strategy import ChunkingStrategy
from atlas.core.errors import AtlasError
from atlas.git.service import RepoService
from atlas.scanner.discovery import DiscoveryService
from atlas.storage.embedding import HashEmbeddingClient
from atlas.storage.pipeline import BuildStorageService
from atlas.storage.sqlite_store import WorkspaceStorage


def build_command(no_sync: bool = typer.Option(False, "--no-sync")) -> None:
    """Build Atlas knowledge base."""
    try:
        if not no_sync:
            sync_results = RepoService().sync()
            failed_sync = [result for result in sync_results if not result.ok]
            for result in sync_results:
                status = "OK" if result.ok else "FAIL"
                commit = result.commit[:12] if result.commit else "-"
                typer.echo(
                    f"[sync:{status}] {result.repo.name}\t{result.action}\t{commit}\t{result.message}"
                )
            if failed_sync:
                raise typer.Exit(code=1)

        discovery = DiscoveryService()
        scan_result = discovery.discover()
        chunker = ChunkingStrategy()
        chunks = chunker.chunk_many(scan_result.files)

        with WorkspaceStorage.from_workspace() as storage:
            run_id = BuildStorageService(storage).write_indexed_chunks(
                chunks=chunks,
                embedding_client=HashEmbeddingClient(),
                synced=(not no_sync),
                repos=discovery.config.repos,
            )

        typer.echo(
            "Build completed: "
            f"run_id={run_id} files={len(scan_result.files)} chunks={len(chunks)} skipped={scan_result.skipped}"
        )
    except AtlasError as exc:
        raise typer.BadParameter(str(exc)) from exc
