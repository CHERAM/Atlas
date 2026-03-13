"""SQLite metadata store and schema bootstrap."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from atlas.core.workspace import detect_workspace_root, ensure_workspace, resolve_workspace_paths
from atlas.storage.errors import StorageError
from atlas.storage.vector_store import LocalVectorStore

_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS repos (
    name TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    branch TEXT NOT NULL,
    local_path TEXT NOT NULL,
    enabled INTEGER NOT NULL,
    last_synced_commit TEXT,
    last_synced_at TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    repo_name TEXT,
    workspace_relative_path TEXT NOT NULL,
    source_relative_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    language_hint TEXT,
    title_hint TEXT,
    content_hash TEXT NOT NULL,
    file_fingerprint TEXT NOT NULL,
    last_indexed_at TEXT NOT NULL,
    UNIQUE(source_type, source_name, workspace_relative_path)
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    section_title TEXT,
    start_line INTEGER,
    end_line INTEGER,
    token_estimate INTEGER NOT NULL,
    text TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(document_id) REFERENCES documents(document_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(chunk_id, document_id);

CREATE TABLE IF NOT EXISTS vectors (
    chunk_id TEXT PRIMARY KEY,
    dim INTEGER NOT NULL,
    vector_json TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    repo_name TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS build_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    synced INTEGER NOT NULL,
    error_text TEXT
);
"""


class WorkspaceStorage:
    """Owns SQLite connection and typed stores for Atlas workspace."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._ensure_schema()
        self.vectors = LocalVectorStore(self.conn)

    @classmethod
    def from_workspace(cls, start_path: Path | None = None) -> "WorkspaceStorage":
        root = detect_workspace_root(start_path)
        config_path = root / "atlas.yaml"
        if not config_path.exists():
            raise StorageError("atlas.yaml not found. Run `atlas init` first.")

        from atlas.core.config import load_config  # Local import to avoid module-level runtime coupling.

        config = load_config(config_path)
        paths = resolve_workspace_paths(root, config)
        ensure_workspace(root, config)
        db_path = paths.index_dir / "atlas-metadata.db"
        return cls(db_path)

    def _ensure_schema(self) -> None:
        try:
            self.conn.executescript(_SCHEMA_SQL)
            self.conn.commit()
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to initialize SQLite schema at {self.db_path}") from exc

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "WorkspaceStorage":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.close()
