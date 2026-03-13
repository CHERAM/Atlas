"""Storage services for Atlas metadata and vectors.

Keep package import lightweight: avoid importing runtime-heavy modules at import time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = [
    "BuildStorageService",
    "EmbeddingClient",
    "HashEmbeddingClient",
    "LocalVectorStore",
    "VectorHit",
    "VectorRecord",
    "WorkspaceStorage",
]

if TYPE_CHECKING:
    from atlas.storage.embedding import EmbeddingClient, HashEmbeddingClient
    from atlas.storage.pipeline import BuildStorageService
    from atlas.storage.sqlite_store import WorkspaceStorage
    from atlas.storage.vector_store import LocalVectorStore, VectorHit, VectorRecord


def __getattr__(name: str) -> Any:
    if name in {"EmbeddingClient", "HashEmbeddingClient"}:
        from atlas.storage.embedding import EmbeddingClient, HashEmbeddingClient

        return {"EmbeddingClient": EmbeddingClient, "HashEmbeddingClient": HashEmbeddingClient}[name]
    if name == "BuildStorageService":
        from atlas.storage.pipeline import BuildStorageService

        return BuildStorageService
    if name == "WorkspaceStorage":
        from atlas.storage.sqlite_store import WorkspaceStorage

        return WorkspaceStorage
    if name in {"LocalVectorStore", "VectorHit", "VectorRecord"}:
        from atlas.storage.vector_store import LocalVectorStore, VectorHit, VectorRecord

        return {
            "LocalVectorStore": LocalVectorStore,
            "VectorHit": VectorHit,
            "VectorRecord": VectorRecord,
        }[name]
    raise AttributeError(name)
