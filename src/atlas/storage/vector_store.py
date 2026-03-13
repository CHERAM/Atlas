"""Vector store abstraction and local SQLite-backed implementation."""

from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass


@dataclass(slots=True)
class VectorRecord:
    chunk_id: str
    vector: list[float]
    source_type: str
    source_name: str
    repo_name: str | None


@dataclass(slots=True)
class VectorHit:
    chunk_id: str
    score: float


class VectorStore:
    """Abstract base for vector persistence and similarity query."""

    def upsert(self, records: list[VectorRecord]) -> None:
        raise NotImplementedError

    def delete_by_chunk_ids(self, chunk_ids: list[str]) -> None:
        raise NotImplementedError

    def query(
        self,
        query_vector: list[float],
        top_k: int,
        filters: dict[str, str] | None = None,
    ) -> list[VectorHit]:
        raise NotImplementedError


class LocalVectorStore(VectorStore):
    """Simple local vector store over SQLite table with in-process scoring."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        self._conn.executemany(
            """
            INSERT INTO vectors (chunk_id, dim, vector_json, source_type, source_name, repo_name, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(chunk_id) DO UPDATE SET
                dim=excluded.dim,
                vector_json=excluded.vector_json,
                source_type=excluded.source_type,
                source_name=excluded.source_name,
                repo_name=excluded.repo_name,
                updated_at=CURRENT_TIMESTAMP
            """,
            [
                (
                    r.chunk_id,
                    len(r.vector),
                    json.dumps(r.vector),
                    r.source_type,
                    r.source_name,
                    r.repo_name,
                )
                for r in records
            ],
        )

    def delete_by_chunk_ids(self, chunk_ids: list[str]) -> None:
        if not chunk_ids:
            return
        placeholders = ",".join(["?"] * len(chunk_ids))
        self._conn.execute(f"DELETE FROM vectors WHERE chunk_id IN ({placeholders})", chunk_ids)

    def query(
        self,
        query_vector: list[float],
        top_k: int,
        filters: dict[str, str] | None = None,
    ) -> list[VectorHit]:
        sql = "SELECT chunk_id, vector_json FROM vectors"
        params: list[str] = []
        clauses: list[str] = []

        if filters:
            for key in ["source_type", "source_name", "repo_name"]:
                if key in filters:
                    clauses.append(f"{key} = ?")
                    params.append(filters[key])

        if clauses:
            sql += " WHERE " + " AND ".join(clauses)

        rows = self._conn.execute(sql, params).fetchall()
        hits: list[VectorHit] = []

        qnorm = _norm(query_vector)
        if qnorm == 0:
            return []

        for row in rows:
            vec = json.loads(row["vector_json"])
            sim = _cosine(query_vector, qnorm, vec)
            if sim <= 0:
                continue
            hits.append(VectorHit(chunk_id=row["chunk_id"], score=sim))

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]


def _norm(vec: list[float]) -> float:
    return math.sqrt(sum(v * v for v in vec))


def _cosine(a: list[float], norm_a: float, b: list[float]) -> float:
    norm_b = _norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    limit = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(limit))
    return dot / (norm_a * norm_b)
