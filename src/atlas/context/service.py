"""Service entrypoint for generating `.github/atlas/context.md`."""

from __future__ import annotations

from pathlib import Path

from atlas.context.assembler import ContextAssembler
from atlas.context.models import ContextPack
from atlas.context.writer import ContextWriter
from atlas.core.config import load_config
from atlas.core.workspace import detect_workspace_root, ensure_workspace, resolve_workspace_paths
from atlas.search.models import SearchResult


class ContextService:
    """Generate context-pack artifacts for AI tools."""

    def __init__(self, start_path: Path | None = None):
        self.root = detect_workspace_root(start_path)
        self.config = load_config(self.root / "atlas.yaml")
        self.paths = resolve_workspace_paths(self.root, self.config)
        ensure_workspace(self.root, self.config)
        self.assembler = ContextAssembler()
        self.writer = ContextWriter()

    def generate_from_results(
        self,
        query: str,
        results: list[SearchResult],
        output_path: Path | None = None,
        allow_all_critical: bool = False,
    ) -> Path:
        context_pack = self.assembler.assemble(
            query=query,
            results=results,
            allow_all_critical=allow_all_critical,
        )
        target = output_path or (self.paths.github_dir / "context.md")
        return self.writer.write(context_pack, target)

    def assemble_only(
        self,
        query: str,
        results: list[SearchResult],
        allow_all_critical: bool = False,
    ) -> ContextPack:
        return self.assembler.assemble(
            query=query,
            results=results,
            allow_all_critical=allow_all_critical,
        )
