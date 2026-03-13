"""Search service facade used by CLI/context flows."""

from __future__ import annotations

from pathlib import Path

from atlas.search.models import SearchResult
from atlas.search.ranking import rank_chunks
from atlas.storage.embedding import EmbeddingClient
from atlas.storage.repositories import MetadataRepository
from atlas.storage.sqlite_store import WorkspaceStorage


class SearchService:
    """Run retrieval across vector index and metadata store."""

    def __init__(self, storage: WorkspaceStorage):
        self.storage = storage
        self.metadata = MetadataRepository(storage.conn)

    @classmethod
    def from_workspace(cls, start_path: Path | None = None) -> "SearchService":
        storage = WorkspaceStorage.from_workspace(start_path)
        return cls(storage)

    def search(
        self,
        query: str,
        embedding_client: EmbeddingClient,
        top_k: int = 20,
        critical_k: int = 5,
        repo_name: str | None = None,
    ) -> list[SearchResult]:
        qvec = embedding_client.embed_query(query)
        filters = {"repo_name": repo_name} if repo_name else None
        hits = self.storage.vectors.query(query_vector=qvec, top_k=top_k, filters=filters)
        chunks = self.metadata.fetch_chunk_views([hit.chunk_id for hit in hits])
        return rank_chunks(hits=hits, chunks=chunks, critical_k=critical_k)

    def close(self) -> None:
        self.storage.close()
