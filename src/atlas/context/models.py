"""Context domain models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ContextSnippet:
    repo_name: str
    file_path: str
    start_line: int | None
    end_line: int | None
    snippet: str
    score: float
    reason: str
    category: str


@dataclass(slots=True)
class ContextPack:
    query: str
    relevant_repositories: list[str]
    architecture_overview: str
    critical_snippets: list[ContextSnippet]
    supporting_snippets: list[ContextSnippet]
    cross_repo_notes: list[str]
    suggested_handoff_prompt: str
