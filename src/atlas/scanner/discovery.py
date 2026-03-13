"""Discovery service for repository and raw web files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from atlas.core.config import load_config
from atlas.core.workspace import detect_workspace_root, ensure_workspace, resolve_workspace_paths
from atlas.scanner.filtering import (
    classify_file_type,
    is_binary_file,
    language_hint,
    should_skip_path,
)
from atlas.scanner.fingerprints import fingerprint_file
from atlas.scanner.models import DiscoveredFile, ScanResult

_SourceType = Literal["repo", "web"]


class DiscoveryService:
    """Discover indexable files across registered repositories and web cache."""

    def __init__(self, start_path: Path | None = None):
        self.root = detect_workspace_root(start_path)
        self.config = load_config(self.root / "atlas.yaml")
        self.paths = resolve_workspace_paths(self.root, self.config)
        ensure_workspace(self.root, self.config)

    def discover(self) -> ScanResult:
        files: list[DiscoveredFile] = []
        skipped = 0

        for repo in self.config.repos:
            if not repo.enabled:
                continue
            repo_dir = self._abs_repo_path(repo.local_path)
            if not repo_dir.exists() or not repo_dir.is_dir():
                continue
            for path in self._iter_files(repo_dir):
                item = self._to_discovered_file(
                    path=path,
                    source_type="repo",
                    source_name=repo.name,
                    source_root=repo_dir,
                    repo_name=repo.name,
                )
                if item is None:
                    skipped += 1
                    continue
                files.append(item)

        web_dir = self.paths.web_dir
        if web_dir.exists():
            for path in self._iter_files(web_dir):
                item = self._to_discovered_file(
                    path=path,
                    source_type="web",
                    source_name="web",
                    source_root=web_dir,
                    repo_name=None,
                )
                if item is None:
                    skipped += 1
                    continue
                files.append(item)

        files.sort(key=lambda item: (item.source_type, item.source_name, item.source_relative_path))
        return ScanResult(files=files, skipped=skipped)

    def _iter_files(self, base_dir: Path):
        for root, dirnames, filenames in os.walk(base_dir):
            root_path = Path(root)
            dirnames[:] = [
                dirname
                for dirname in dirnames
                if not should_skip_path((root_path / dirname).relative_to(base_dir))
            ]
            for filename in filenames:
                path = root_path / filename
                if path.is_file():
                    yield path

    def _to_discovered_file(
        self,
        path: Path,
        source_type: _SourceType,
        source_name: str,
        source_root: Path,
        repo_name: str | None,
    ) -> DiscoveredFile | None:
        if should_skip_path(path.relative_to(source_root)):
            return None

        file_type = classify_file_type(path)
        if file_type is None:
            return None

        max_bytes = self.config.build.max_file_bytes
        try:
            size = path.stat().st_size
        except OSError:
            return None

        if size > max_bytes:
            return None

        if is_binary_file(path):
            return None

        fp = fingerprint_file(path)
        source_rel = path.relative_to(source_root).as_posix()
        workspace_rel = path.relative_to(self.root).as_posix()
        return DiscoveredFile(
            source_type=source_type,
            file_type=file_type,
            abs_path=path,
            workspace_relative_path=workspace_rel,
            source_relative_path=source_rel,
            source_name=source_name,
            repo_name=repo_name,
            title_hint=self._title_hint(path),
            language_hint=language_hint(path, file_type),
            size_bytes=fp.size_bytes,
            content_hash=fp.content_hash,
            fingerprint=fp.fingerprint,
            mtime_ns=fp.mtime_ns,
        )

    def _abs_repo_path(self, configured_local_path: str) -> Path:
        candidate = Path(configured_local_path)
        return candidate if candidate.is_absolute() else self.root / candidate

    @staticmethod
    def _title_hint(path: Path) -> str | None:
        name = path.stem.replace("_", " ").replace("-", " ").strip()
        return name or None
