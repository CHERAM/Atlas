"""Search domain models."""

from __future__ import annotations

from dataclasses import dataclass

from atlas.storage.models import Category


@dataclass(slots=True)
class SearchResult:
    result_id: str
    repo_name: str
    file_path: str
    start_line: int | None
    end_line: int | None
    snippet: str
    score: float
    reason: str
    category: Category
    is_critical: bool
