"""Data models for web source registration and ingestion output."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RegisteredWebSource:
    """Normalized web source model used by web services."""

    source_id: str
    url: str
    kind: str
    enabled: bool = True


@dataclass(slots=True)
class IngestResult:
    """Result payload for one-time web ingestion runs."""

    source_id: str
    url: str
    ok: bool
    html_path: Path | None
    metadata_path: Path | None
    message: str
