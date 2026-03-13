"""Chunking output models used by downstream indexing/storage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from atlas.scanner.models import FileType, SourceType


@dataclass(slots=True)
class IndexChunk:
    """Single chunk emitted from a discovered file."""

    chunk_id: str
    source_type: SourceType
    source_name: str
    repo_name: str | None
    workspace_relative_path: str
    source_relative_path: str
    file_type: FileType
    language_hint: str | None
    title_hint: str | None
    section_title: str | None
    chunk_index: int
    start_line: int | None
    end_line: int | None
    token_estimate: int
    text: str
    content_hash: str
    file_fingerprint: str
    metadata: dict[str, Any]
