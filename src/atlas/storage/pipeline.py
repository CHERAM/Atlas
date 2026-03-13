"""Helpers to persist indexed chunks and vectors during build."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime

from atlas.chunking.models import IndexChunk
from atlas.core.models import RepoConfig
from atlas.storage.embedding import EmbeddingClient
from atlas.storage.models import DocumentRecord
from atlas.storage.repositories import MetadataRepository, chunk_records_for_document
from atlas.storage.sqlite_store import WorkspaceStorage
from atlas.storage.vector_store import VectorRecord


class BuildStorageService:
    """Coordinates metadata + vector persistence for indexed chunks."""

    def __init__(self, storage: WorkspaceStorage):
        self.storage = storage
        self.repo = MetadataRepository(storage.conn)

    def write_indexed_chunks(
        self,
        chunks: list[IndexChunk],
        embedding_client: EmbeddingClient,
        synced: bool = True,
        repos: list[RepoConfig] | None = None,
    ) -> str:
        run_id = str(uuid.uuid4())
        self.repo.start_build_run(run_id, synced=synced)

        try:
            if repos:
                for repo in repos:
                    self.repo.upsert_repo(repo)

            by_document: dict[str, list[IndexChunk]] = defaultdict(list)
            for chunk in chunks:
                by_document[_document_id(chunk)].append(chunk)

            for doc_id, doc_chunks in by_document.items():
                first = doc_chunks[0]
                record = DocumentRecord(
                    document_id=doc_id,
                    source_type=first.source_type,
                    source_name=first.source_name,
                    repo_name=first.repo_name,
                    workspace_relative_path=first.workspace_relative_path,
                    source_relative_path=first.source_relative_path,
                    file_type=first.file_type,
                    language_hint=first.language_hint,
                    title_hint=first.title_hint,
                    content_hash=first.content_hash,
                    file_fingerprint=first.file_fingerprint,
                    last_indexed_at=datetime.now(UTC).isoformat(),
                )
                self.repo.upsert_document(record)

                old_ids = set(self.repo.list_all_chunk_ids_for_document(doc_id))
                chunk_rows = chunk_records_for_document(doc_id, doc_chunks)
                self.repo.replace_document_chunks(doc_id, chunk_rows)
                new_ids = {c.chunk_id for c in chunk_rows}
                stale_ids = list(old_ids - new_ids)
                if stale_ids:
                    self.storage.vectors.delete_by_chunk_ids(stale_ids)

                vectors = embedding_client.embed_texts([c.text for c in doc_chunks])
                vector_records = [
                    VectorRecord(
                        chunk_id=c.chunk_id,
                        vector=vectors[idx],
                        source_type=c.source_type,
                        source_name=c.source_name,
                        repo_name=c.repo_name,
                    )
                    for idx, c in enumerate(doc_chunks)
                ]
                self.storage.vectors.upsert(vector_records)

            self.repo.finish_build_run(run_id, ok=True)
            self.storage.conn.commit()
            return run_id
        except Exception as exc:
            self.repo.finish_build_run(run_id, ok=False, error_text=str(exc))
            self.storage.conn.commit()
            raise


def _document_id(chunk: IndexChunk) -> str:
    key = f"{chunk.source_type}|{chunk.source_name}|{chunk.workspace_relative_path}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))
