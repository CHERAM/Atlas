"""Domain models used by storage and search layers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from atlas.scanner.models import FileType, SourceType

Category = Literal["architecture", "integration", "interface", "execution", "supporting"]


@dataclass(slots=True)
class DocumentRecord:
    document_id: str
    source_type: SourceType
    source_name: str
    repo_name: str | None
    workspace_relative_path: str
    source_relative_path: str
    file_type: FileType
    language_hint: str | None
    title_hint: str | None
    content_hash: str
    file_fingerprint: str
    last_indexed_at: str


@dataclass(slots=True)
class ChunkRecord:
    chunk_id: str
    document_id: str
    chunk_index: int
    section_title: str | None
    start_line: int | None
    end_line: int | None
    text: str
    token_estimate: int
    metadata_json: str


@dataclass(slots=True)
class ChunkView:
    chunk_id: str
    document_id: str
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
    text: str
    token_estimate: int
    content_hash: str
    metadata_json: str
