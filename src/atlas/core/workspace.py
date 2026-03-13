"""Workspace detection and bootstrap utilities."""

from __future__ import annotations

from pathlib import Path

from atlas.core.errors import WorkspaceError
from atlas.core.models import AtlasConfig, WorkspacePaths

CONFIG_FILENAME = "atlas.yaml"


def detect_workspace_root(start: Path | None = None) -> Path:
    """Find workspace root by searching upward for `atlas.yaml`.

    If no config is found, use the provided start directory (or cwd).
    """
    cursor = (start or Path.cwd()).resolve()
    search_dir = cursor if cursor.is_dir() else cursor.parent

    for candidate in [search_dir, *search_dir.parents]:
        if (candidate / CONFIG_FILENAME).exists():
            return candidate

    return search_dir


def resolve_workspace_paths(
    root: Path, config: AtlasConfig | None = None
) -> WorkspacePaths:
    """Resolve absolute workspace paths from root and config values."""
    cfg = config or AtlasConfig()
    return WorkspacePaths(
        root=root,
        github_dir=root / cfg.workspace.github_dir,
        prompts_dir=root / cfg.workspace.prompts_dir,
        books_dir=root / cfg.workspace.books_dir,
        cache_dir=root / cfg.workspace.cache_dir,
        repos_dir=root / cfg.workspace.repos_dir,
        index_dir=root / cfg.workspace.index_dir,
        web_dir=root / cfg.workspace.web_dir,
        config_path=root / CONFIG_FILENAME,
    )


def ensure_workspace(root: Path, config: AtlasConfig | None = None) -> WorkspacePaths:
    """Create expected workspace directories.

    Raises `WorkspaceError` for unrecoverable filesystem errors.
    """
    paths = resolve_workspace_paths(root, config)
    try:
        for directory in [
            paths.github_dir,
            paths.prompts_dir,
            paths.books_dir,
            paths.cache_dir,
            paths.repos_dir,
            paths.index_dir,
            paths.web_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise WorkspaceError(f"Failed to initialize workspace under {root}") from exc

    return paths
