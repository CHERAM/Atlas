"""Markdown writer for Atlas context-pack output."""

from __future__ import annotations

from pathlib import Path

from atlas.context.models import ContextPack, ContextSnippet


class ContextWriter:
    """Writes context-pack markdown files for AI handoff."""

    def write(self, context: ContextPack, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self._to_markdown(context), encoding="utf-8")
        return output_path

    def _to_markdown(self, context: ContextPack) -> str:
        sections = [
            "# Atlas Context Pack",
            "",
            "## Query",
            context.query,
            "",
            "## Relevant Repositories",
            *self._repo_lines(context.relevant_repositories),
            "",
            "## Architecture Overview",
            context.architecture_overview,
            "",
            "## Critical Snippets",
            *self._snippet_lines(context.critical_snippets),
            "",
            "## Supporting Snippets",
            *self._snippet_lines(context.supporting_snippets),
            "",
            "## Cross-Repo Notes",
            *self._note_lines(context.cross_repo_notes),
            "",
            "## Suggested Prompt For AI Agent Usage",
            context.suggested_handoff_prompt,
            "",
        ]
        return "\n".join(sections)

    @staticmethod
    def _repo_lines(repos: list[str]) -> list[str]:
        if not repos:
            return ["- none"]
        return [f"- {repo}" for repo in repos]

    @staticmethod
    def _note_lines(notes: list[str]) -> list[str]:
        if not notes:
            return ["- none"]
        return [f"- {note}" for note in notes]

    def _snippet_lines(self, snippets: list[ContextSnippet]) -> list[str]:
        if not snippets:
            return ["- none"]

        lines: list[str] = []
        for snippet in snippets:
            line_range = (
                f"{snippet.start_line}-{snippet.end_line}"
                if snippet.start_line is not None and snippet.end_line is not None
                else "n/a"
            )
            cleaned = self._single_line(snippet.snippet)
            lines.append(
                f"- `{snippet.repo_name}` | `{snippet.file_path}` | lines `{line_range}` "
                f"| score `{snippet.score:.3f}` | {snippet.reason}"
            )
            lines.append(f"  - {cleaned}")
        return lines

    @staticmethod
    def _single_line(text: str, max_len: int = 320) -> str:
        compact = " ".join(text.split())
        if len(compact) <= max_len:
            return compact
        return compact[: max_len - 3] + "..."
