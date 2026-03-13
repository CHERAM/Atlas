"""DAO-style accessors for SQLite metadata tables."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from atlas.chunking.models import IndexChunk
from atlas.core.models import RepoConfig
from atlas.storage.models import ChunkRecord, ChunkView, DocumentRecord


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


class MetadataRepository:
    """Persist and query metadata records."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def upsert_repo(self, repo: RepoConfig, last_commit: str | None = None) -> None:
        self._conn.execute(
            """
            INSERT INTO repos (name, url, branch, local_path, enabled, last_synced_commit, last_synced_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
              url=excluded.url,
              branch=excluded.branch,
              local_path=excluded.local_path,
              enabled=excluded.enabled,
              last_synced_commit=COALESCE(excluded.last_synced_commit, repos.last_synced_commit),
              last_synced_at=CASE WHEN excluded.last_synced_commit IS NULL THEN repos.last_synced_at ELSE excluded.last_synced_at END,
              updated_at=CURRENT_TIMESTAMP
            """,
            (
                repo.name,
                repo.url,
                repo.branch,
                repo.local_path,
                1 if repo.enabled else 0,
                last_commit,
                now_utc() if last_commit else None,
            ),
        )

    def upsert_document(self, record: DocumentRecord) -> None:
        self._conn.execute(
            """
            INSERT INTO documents (
                document_id, source_type, source_name, repo_name, workspace_relative_path,
                source_relative_path, file_type, language_hint, title_hint, content_hash,
                file_fingerprint, last_indexed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(document_id) DO UPDATE SET
                source_type=excluded.source_type,
                source_name=excluded.source_name,
                repo_name=excluded.repo_name,
                workspace_relative_path=excluded.workspace_relative_path,
                source_relative_path=excluded.source_relative_path,
                file_type=excluded.file_type,
                language_hint=excluded.language_hint,
                title_hint=excluded.title_hint,
                content_hash=excluded.content_hash,
                file_fingerprint=excluded.file_fingerprint,
                last_indexed_at=excluded.last_indexed_at
            """,
            (
                record.document_id,
                record.source_type,
                record.source_name,
                record.repo_name,
                record.workspace_relative_path,
                record.source_relative_path,
                record.file_type,
                record.language_hint,
                record.title_hint,
                record.content_hash,
                record.file_fingerprint,
                record.last_indexed_at,
            ),
        )

    def replace_document_chunks(self, document_id: str, chunks: list[ChunkRecord]) -> None:
        self._conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
        if not chunks:
            return

        self._conn.executemany(
            """
            INSERT INTO chunks (
                chunk_id, document_id, chunk_index, section_title, start_line, end_line,
                token_estimate, text, metadata_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [
                (
                    c.chunk_id,
                    c.document_id,
                    c.chunk_index,
                    c.section_title,
                    c.start_line,
                    c.end_line,
                    c.token_estimate,
                    c.text,
                    c.metadata_json,
                )
                for c in chunks
            ],
        )

    def fetch_chunk_views(self, chunk_ids: list[str]) -> list[ChunkView]:
        if not chunk_ids:
            return []
        placeholders = ",".join(["?"] * len(chunk_ids))
        rows = self._conn.execute(
            f"""
            SELECT
                c.chunk_id,
                c.document_id,
                d.source_type,
                d.source_name,
                d.repo_name,
                d.workspace_relative_path,
                d.source_relative_path,
                d.file_type,
                d.language_hint,
                d.title_hint,
                c.section_title,
                c.chunk_index,
                c.start_line,
                c.end_line,
                c.text,
                c.token_estimate,
                d.content_hash,
                c.metadata_json
            FROM chunks c
            JOIN documents d ON d.document_id = c.document_id
            WHERE c.chunk_id IN ({placeholders})
            """,
            chunk_ids,
        ).fetchall()

        by_id = {row["chunk_id"]: _row_to_chunk_view(row) for row in rows}
        return [by_id[cid] for cid in chunk_ids if cid in by_id]

    def list_all_chunk_ids_for_document(self, document_id: str) -> list[str]:
        rows = self._conn.execute(
            "SELECT chunk_id FROM chunks WHERE document_id = ?",
            (document_id,),
        ).fetchall()
        return [r["chunk_id"] for r in rows]

    def start_build_run(self, run_id: str, synced: bool) -> None:
        self._conn.execute(
            "INSERT INTO build_runs (run_id, started_at, status, synced) VALUES (?, ?, ?, ?)",
            (run_id, now_utc(), "running", 1 if synced else 0),
        )

    def finish_build_run(self, run_id: str, ok: bool, error_text: str | None = None) -> None:
        self._conn.execute(
            """
            UPDATE build_runs
            SET finished_at = ?, status = ?, error_text = ?
            WHERE run_id = ?
            """,
            (now_utc(), "success" if ok else "failed", error_text, run_id),
        )


def chunk_records_for_document(document_id: str, chunks: list[IndexChunk]) -> list[ChunkRecord]:
    return [
        ChunkRecord(
            chunk_id=chunk.chunk_id,
            document_id=document_id,
            chunk_index=chunk.chunk_index,
            section_title=chunk.section_title,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            text=chunk.text,
            token_estimate=chunk.token_estimate,
            metadata_json=json.dumps(chunk.metadata),
        )
        for chunk in chunks
    ]


def _row_to_chunk_view(row: sqlite3.Row) -> ChunkView:
    return ChunkView(
        chunk_id=row["chunk_id"],
        document_id=row["document_id"],
        source_type=row["source_type"],
        source_name=row["source_name"],
        repo_name=row["repo_name"],
        workspace_relative_path=row["workspace_relative_path"],
        source_relative_path=row["source_relative_path"],
        file_type=row["file_type"],
        language_hint=row["language_hint"],
        title_hint=row["title_hint"],
        section_title=row["section_title"],
        chunk_index=row["chunk_index"],
        start_line=row["start_line"],
        end_line=row["end_line"],
        text=row["text"],
        token_estimate=row["token_estimate"],
        content_hash=row["content_hash"],
        metadata_json=row["metadata_json"],
    )
