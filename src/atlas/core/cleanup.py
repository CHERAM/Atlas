"""Workspace cleanup helpers for Atlas."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from atlas.core.config import load_config
from atlas.core.models import AtlasConfig
from atlas.core.workspace import CONFIG_FILENAME, detect_workspace_root, resolve_workspace_paths


@dataclass(frozen=True, slots=True)
class CleanupTargets:
    root: Path
    cache_dir: Path
    github_dir: Path
    books_dir: Path
    config_path: Path


def resolve_cleanup_targets(start_path: Path | None = None) -> CleanupTargets:
    root = detect_workspace_root(start_path)
    config_path = root / CONFIG_FILENAME

    if config_path.exists():
        config = load_config(config_path)
    else:
        config = AtlasConfig()

    paths = resolve_workspace_paths(root, config)
    return CleanupTargets(
        root=root,
        cache_dir=paths.cache_dir,
        github_dir=paths.github_dir,
        books_dir=paths.books_dir,
        config_path=paths.config_path,
    )


def remove_cache_only(start_path: Path | None = None) -> list[Path]:
    targets = resolve_cleanup_targets(start_path)
    removed: list[Path] = []
    if _safe_remove_dir(targets.cache_dir, targets.root):
        removed.append(targets.cache_dir)
    return removed


def remove_hard_reset(start_path: Path | None = None) -> list[Path]:
    targets = resolve_cleanup_targets(start_path)
    removed: list[Path] = []
    if _safe_remove_dir(targets.cache_dir, targets.root):
        removed.append(targets.cache_dir)
    if _safe_remove_dir(targets.github_dir, targets.root):
        removed.append(targets.github_dir)
    if _safe_remove_dir(targets.books_dir, targets.root):
        removed.append(targets.books_dir)
    if _safe_remove_file(targets.config_path, targets.root):
        removed.append(targets.config_path)
    return removed


def _safe_remove_dir(path: Path, root: Path) -> bool:
    if not path.exists():
        return False
    if not _is_under_root(path, root):
        return False
    shutil.rmtree(path)
    return True


def _safe_remove_file(path: Path, root: Path) -> bool:
    if not path.exists():
        return False
    if not _is_under_root(path, root):
        return False
    path.unlink()
    return True


def _is_under_root(path: Path, root: Path) -> bool:
    try:
        return path.resolve().is_relative_to(root.resolve())
    except OSError:
        return False
