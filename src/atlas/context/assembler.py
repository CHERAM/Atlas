"""Assemble context-pack content from ranked search results."""

from __future__ import annotations

from collections import defaultdict

from atlas.context.models import ContextPack, ContextSnippet
from atlas.search.models import SearchResult


class ContextAssembler:
    """Transforms ranked search results into context sections for AI handoff."""

    def assemble(
        self,
        query: str,
        results: list[SearchResult],
        critical_limit: int = 5,
        allow_all_critical: bool = False,
    ) -> ContextPack:
        filtered_results = self._dedupe_results_for_context(results)
        snippets = [self._to_context_snippet(result) for result in filtered_results]

        critical = [s for idx, s in enumerate(snippets) if filtered_results[idx].is_critical]
        supporting = [s for idx, s in enumerate(snippets) if not filtered_results[idx].is_critical]

        if not critical and snippets:
            critical = snippets[:critical_limit]
            supporting = snippets[critical_limit:]

        if len(snippets) > 1 and not allow_all_critical:
            if not supporting and critical:
                supporting = [critical.pop()]
            if not critical and supporting:
                critical = [supporting.pop(0)]

        relevant_repositories = sorted({snippet.repo_name for snippet in snippets})
        architecture_overview = self._architecture_overview(query, snippets)
        cross_repo_notes = self._cross_repo_notes(snippets)
        suggested_prompt = self._suggested_prompt(
            query=query,
            repos=relevant_repositories,
            critical=critical,
            supporting=supporting,
        )

        return ContextPack(
            query=query,
            relevant_repositories=relevant_repositories,
            architecture_overview=architecture_overview,
            critical_snippets=critical,
            supporting_snippets=supporting,
            cross_repo_notes=cross_repo_notes,
            suggested_handoff_prompt=suggested_prompt,
        )

    @staticmethod
    def _to_context_snippet(result: SearchResult) -> ContextSnippet:
        return ContextSnippet(
            repo_name=result.repo_name,
            file_path=result.file_path,
            start_line=result.start_line,
            end_line=result.end_line,
            snippet=result.snippet,
            score=result.score,
            reason=result.reason,
            category=result.category,
        )

    def _architecture_overview(self, query: str, snippets: list[ContextSnippet]) -> str:
        if not snippets:
            return (
                f"No indexed results were found for query '{query}'. "
                "Run `atlas build` and retry if indexing has not been completed."
            )

        category_counts: dict[str, int] = defaultdict(int)
        for snippet in snippets:
            category_counts[snippet.category] += 1

        ordered_categories = sorted(category_counts.items(), key=lambda item: item[1], reverse=True)
        top_categories = ", ".join(f"{name} ({count})" for name, count in ordered_categories[:3])
        top_repos = sorted({snippet.repo_name for snippet in snippets[:8]})

        return (
            "Architecture-first evidence prioritized from ranked search results. "
            f"Top signal categories: {top_categories}. "
            f"Primary repositories in top results: {', '.join(top_repos)}."
        )

    def _cross_repo_notes(self, snippets: list[ContextSnippet]) -> list[str]:
        if not snippets:
            return ["No cross-repo observations available."]

        by_repo: dict[str, list[ContextSnippet]] = defaultdict(list)
        for snippet in snippets:
            by_repo[snippet.repo_name].append(snippet)

        repos = sorted(by_repo.keys())
        notes: list[str] = []

        if len(repos) > 1:
            notes.append(f"Results span {len(repos)} repositories: {', '.join(repos)}.")
        else:
            notes.append(f"Results are concentrated in repository: {repos[0]}.")

        for repo_name in repos[:5]:
            repo_snippets = by_repo[repo_name]
            top_categories = sorted(
                {snippet.category for snippet in repo_snippets[:6]}
            )
            top_paths = _ordered_unique([s.file_path for s in repo_snippets])[:2]
            notes.append(
                f"{repo_name}: strongest categories -> {', '.join(top_categories)}; "
                f"top files include {', '.join(top_paths) if top_paths else 'none'}."
            )

        return notes

    def _suggested_prompt(
        self,
        query: str,
        repos: list[str],
        critical: list[ContextSnippet],
        supporting: list[ContextSnippet],
    ) -> str:
        critical_paths_list = _ordered_unique([snippet.file_path for snippet in critical])[:5]
        supporting_paths_list = _ordered_unique([snippet.file_path for snippet in supporting])[:5]
        critical_paths = ", ".join(critical_paths_list) or "none"
        supporting_paths = ", ".join(supporting_paths_list) or "none"

        return (
            "You are assisting with Atlas cross-repository analysis. "
            f"Focus on query: '{query}'. "
            f"Start from architecture-critical files: {critical_paths}. "
            f"Use supporting evidence from: {supporting_paths}. "
            f"Repositories in scope: {', '.join(repos) if repos else 'none'}. "
            "Explain integration points first, then interfaces, then execution-path details. "
            "Call out assumptions and unknowns explicitly."
        )

    def _dedupe_results_for_context(self, results: list[SearchResult]) -> list[SearchResult]:
        """Deduplicate low-value repetition for context output quality."""
        if not results:
            return []

        deduped: list[SearchResult] = []
        seen_exact: set[tuple[str, str, str]] = set()
        previous_key: tuple[str, str] | None = None

        for result in results:
            normalized_text = " ".join(result.snippet.split())
            exact_key = (result.repo_name, result.file_path, normalized_text)
            if exact_key in seen_exact:
                continue

            file_key = (result.repo_name, result.file_path)
            # Reduce adjacent same-file chunk repetition in context pack.
            if previous_key == file_key:
                continue

            seen_exact.add(exact_key)
            deduped.append(result)
            previous_key = file_key

        return deduped


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
