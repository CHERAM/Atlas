"""Models for scanner discovery outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SourceType = Literal["repo", "web"]
FileType = Literal["markdown", "html", "config", "code", "text"]


@dataclass(slots=True)
class DiscoveredFile:
    """Canonical representation of a file discovered for indexing."""

    source_type: SourceType
    file_type: FileType
    abs_path: Path
    workspace_relative_path: str
    source_relative_path: str
    source_name: str
    repo_name: str | None
    title_hint: str | None
    language_hint: str | None
    size_bytes: int
    content_hash: str
    fingerprint: str
    mtime_ns: int

    @property
    def source_id(self) -> str:
        if self.source_type == "repo":
            return f"repo:{self.source_name}"
        return f"web:{self.source_name}"


@dataclass(slots=True)
class ScanResult:
    """Batch result for scanner output."""

    files: list[DiscoveredFile]
    skipped: int
