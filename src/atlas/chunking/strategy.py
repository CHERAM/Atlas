"""MVP chunking strategy with section-aware doc chunking and code fallback."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from atlas.chunking.models import IndexChunk
from atlas.scanner.models import DiscoveredFile

_MD_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_HTML_HEADING = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
_HTML_TAG = re.compile(r"<[^>]+>")


@dataclass(slots=True)
class _Section:
    title: str | None
    start_line: int
    lines: list[str]


class ChunkingStrategy:
    """Chunker that preserves architectural context metadata where possible."""

    def __init__(self, max_chars: int = 1800, overlap_lines: int = 8):
        self.max_chars = max_chars
        self.overlap_lines = overlap_lines

    def chunk_file(self, file: DiscoveredFile) -> list[IndexChunk]:
        text = self._read_text(file)
        if not text.strip():
            return []

        if file.file_type == "markdown":
            sections = self._markdown_sections(text)
            return self._chunk_sections(file, sections)
        if file.file_type == "html":
            sections = self._html_sections(text)
            return self._chunk_sections(file, sections)

        return self._chunk_by_lines(file=file, text=text, section_title=None, start_line_offset=1)

    def chunk_many(self, files: list[DiscoveredFile]) -> list[IndexChunk]:
        chunks: list[IndexChunk] = []
        for file in files:
            chunks.extend(self.chunk_file(file))
        return chunks

    @staticmethod
    def _read_text(file: DiscoveredFile) -> str:
        try:
            return file.abs_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ""

    def _markdown_sections(self, text: str) -> list[_Section]:
        lines = text.splitlines()
        sections: list[_Section] = []
        current = _Section(title=None, start_line=1, lines=[])

        for idx, line in enumerate(lines, start=1):
            heading = _MD_HEADING.match(line)
            if heading and current.lines:
                sections.append(current)
                current = _Section(title=heading.group(2).strip(), start_line=idx, lines=[line])
                continue

            if heading and not current.lines:
                current.title = heading.group(2).strip()

            current.lines.append(line)

        if current.lines:
            sections.append(current)

        return sections

    def _html_sections(self, text: str) -> list[_Section]:
        plain = self._html_to_text(text)
        lines = plain.splitlines()

        sections: list[_Section] = []
        current = _Section(title=None, start_line=1, lines=[])
        heading_re = re.compile(r"^#{1,6}\s+(.*)$")

        for idx, line in enumerate(lines, start=1):
            heading = heading_re.match(line)
            if heading:
                if current.lines:
                    sections.append(current)
                current = _Section(title=heading.group(1).strip(), start_line=idx, lines=[line])
            else:
                current.lines.append(line)

        if current.lines:
            sections.append(current)

        return sections

    def _html_to_text(self, html: str) -> str:
        content = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r"<style[^>]*>.*?</style>", "", content, flags=re.IGNORECASE | re.DOTALL)

        # Promote heading tags to markdown-like headings to retain section context.
        def heading_repl(match: re.Match[str]) -> str:
            level = int(match.group(1))
            label = self._strip_html(match.group(2)).strip()
            return f"\n{'#' * level} {label}\n"

        content = _HTML_HEADING.sub(heading_repl, content)
        content = self._strip_html(content)
        content = re.sub(r"\n{3,}", "\n\n", content)
        return content.strip()

    @staticmethod
    def _strip_html(raw: str) -> str:
        return _HTML_TAG.sub("", raw)

    def _chunk_sections(self, file: DiscoveredFile, sections: list[_Section]) -> list[IndexChunk]:
        chunks: list[IndexChunk] = []
        chunk_index = 0
        for section in sections:
            section_text = "\n".join(section.lines).strip()
            if not section_text:
                continue
            section_chunks = self._chunk_by_lines(
                file=file,
                text=section_text,
                section_title=section.title,
                start_line_offset=section.start_line,
                base_chunk_index=chunk_index,
            )
            chunks.extend(section_chunks)
            chunk_index += len(section_chunks)
        return chunks

    def _chunk_by_lines(
        self,
        file: DiscoveredFile,
        text: str,
        section_title: str | None,
        start_line_offset: int,
        base_chunk_index: int = 0,
    ) -> list[IndexChunk]:
        lines = text.splitlines() or [text]
        chunks: list[IndexChunk] = []
        i = 0
        local_chunk_idx = 0

        while i < len(lines):
            current: list[str] = []
            chars = 0
            start = i

            while i < len(lines):
                line = lines[i]
                projected = chars + len(line) + 1
                if current and projected > self.max_chars:
                    break
                current.append(line)
                chars = projected
                i += 1

            chunk_text = "\n".join(current).strip()
            if not chunk_text:
                i += 1
                continue

            start_line = start_line_offset + start
            end_line = start_line_offset + i - 1
            chunk_index = base_chunk_index + local_chunk_idx
            chunks.append(
                self._build_chunk(
                    file=file,
                    text=chunk_text,
                    section_title=section_title,
                    start_line=start_line,
                    end_line=end_line,
                    chunk_index=chunk_index,
                )
            )
            local_chunk_idx += 1

            if i < len(lines):
                i = max(i - self.overlap_lines, start + 1)

        return chunks

    def _build_chunk(
        self,
        file: DiscoveredFile,
        text: str,
        section_title: str | None,
        start_line: int | None,
        end_line: int | None,
        chunk_index: int,
    ) -> IndexChunk:
        token_estimate = max(1, len(text) // 4)
        chunk_id = self._chunk_id(file=file, text=text, section_title=section_title, chunk_index=chunk_index)
        metadata = {
            "source_id": file.source_id,
            "file_type": file.file_type,
            "path": file.workspace_relative_path,
            "section": section_title,
            "architecture_hint": file.file_type in {"markdown", "html"},
            "is_readme": file.source_relative_path.lower().startswith("readme"),
        }

        return IndexChunk(
            chunk_id=chunk_id,
            source_type=file.source_type,
            source_name=file.source_name,
            repo_name=file.repo_name,
            workspace_relative_path=file.workspace_relative_path,
            source_relative_path=file.source_relative_path,
            file_type=file.file_type,
            language_hint=file.language_hint,
            title_hint=file.title_hint,
            section_title=section_title,
            chunk_index=chunk_index,
            start_line=start_line,
            end_line=end_line,
            token_estimate=token_estimate,
            text=text,
            content_hash=file.content_hash,
            file_fingerprint=file.fingerprint,
            metadata=metadata,
        )

    @staticmethod
    def _chunk_id(
        file: DiscoveredFile,
        text: str,
        section_title: str | None,
        chunk_index: int,
    ) -> str:
        basis = "|".join(
            [
                file.source_id,
                file.workspace_relative_path,
                file.content_hash,
                section_title or "",
                str(chunk_index),
                hashlib.sha1(text.encode("utf-8")).hexdigest(),
            ]
        )
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()
