"""Search services and result formatting.

Keep package import lightweight: avoid importing runtime-heavy modules at import time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["SearchResult", "SearchService", "format_search_results"]

if TYPE_CHECKING:
    from atlas.search.models import SearchResult
    from atlas.search.service import SearchService


def __getattr__(name: str) -> Any:
    if name == "SearchResult":
        from atlas.search.models import SearchResult

        return SearchResult
    if name == "SearchService":
        from atlas.search.service import SearchService

        return SearchService
    if name == "format_search_results":
        from atlas.search.formatter import format_search_results

        return format_search_results
    raise AttributeError(name)
