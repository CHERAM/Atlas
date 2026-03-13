"""Search ranking logic combining vector similarity and architecture-first metadata boosts."""

from __future__ import annotations

import json
from dataclasses import dataclass

from atlas.search.models import SearchResult
from atlas.storage.models import Category, ChunkView
from atlas.storage.vector_store import VectorHit


@dataclass(slots=True)
class RankedChunk:
    chunk: ChunkView
    score: float
    reason: str
    category: Category


def rank_chunks(hits: list[VectorHit], chunks: list[ChunkView], critical_k: int = 5) -> list[SearchResult]:
    chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    ranked: list[RankedChunk] = []

    for hit in hits:
        chunk = chunk_by_id.get(hit.chunk_id)
        if chunk is None:
            continue

        metadata = _safe_json(chunk.metadata_json)
        score = hit.score
        reasons: list[str] = [f"vector={hit.score:.3f}"]

        if metadata.get("architecture_hint"):
            score += 0.18
            reasons.append("architecture-doc-boost")

        if metadata.get("is_readme"):
            score += 0.12
            reasons.append("readme-boost")

        if chunk.file_type == "config":
            score += 0.07
            reasons.append("config-wiring-boost")

        if chunk.section_title:
            score += 0.03
            reasons.append("section-context")

        category = categorize_chunk(chunk, metadata)
        ranked.append(RankedChunk(chunk=chunk, score=score, reason=", ".join(reasons), category=category))

    ranked.sort(key=lambda r: r.score, reverse=True)

    results: list[SearchResult] = []
    for idx, item in enumerate(ranked):
        repo = item.chunk.repo_name or item.chunk.source_name
        results.append(
            SearchResult(
                result_id=item.chunk.chunk_id,
                repo_name=repo,
                file_path=_display_path(item.chunk),
                start_line=item.chunk.start_line,
                end_line=item.chunk.end_line,
                snippet=item.chunk.text,
                score=item.score,
                reason=item.reason,
                category=item.category,
                is_critical=idx < critical_k,
            )
        )

    return results


def categorize_chunk(chunk: ChunkView, metadata: dict) -> Category:
    if metadata.get("architecture_hint"):
        return "architecture"

    path = chunk.workspace_relative_path.lower()
    if any(token in path for token in ["router", "wiring", "bootstrap", "main", "app", "entry"]):
        return "integration"

    if any(token in path for token in ["interface", "protocol", "contract", "schema", "types"]):
        return "interface"

    if chunk.file_type in {"code", "config"}:
        return "execution"

    return "supporting"


def _safe_json(payload: str) -> dict:
    try:
        parsed = json.loads(payload)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _display_path(chunk: ChunkView) -> str:
    """Return user-facing path while preserving raw path in metadata storage."""
    path = chunk.workspace_relative_path
    if chunk.source_type != "repo" or not chunk.repo_name:
        return path

    prefix = f".atlas-cache/repos/{chunk.repo_name}/"
    root_prefix = f".atlas-cache/repos/{chunk.repo_name}"
    if path == root_prefix:
        return "."
    if path.startswith(prefix):
        return path[len(prefix) :]
    return path
