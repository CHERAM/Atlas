"""Formatting contract for atlas search terminal output."""

from __future__ import annotations

from atlas.search.models import SearchResult


def format_search_results(results: list[SearchResult]) -> str:
    """Render search results with required Atlas fields."""
    if not results:
        return "No search results found."

    lines: list[str] = []
    for idx, item in enumerate(results, start=1):
        line_range = (
            f"{item.start_line}-{item.end_line}"
            if item.start_line is not None and item.end_line is not None
            else "n/a"
        )
        snippet = _truncate(item.snippet.replace("\n", " "), 280)
        critical = "critical" if item.is_critical else "supporting"
        lines.extend(
            [
                f"[{idx}] {item.repo_name} :: {item.file_path}",
                f"  lines: {line_range} | score: {item.score:.3f} | category: {item.category} ({critical})",
                f"  reason: {item.reason}",
                f"  snippet: {snippet}",
            ]
        )

    return "\n".join(lines)


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
