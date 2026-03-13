"""Core shared utilities for Atlas."""

from atlas.core.config import AtlasConfig, load_or_create_config, load_config, save_config
from atlas.core.workspace import WorkspacePaths, detect_workspace_root, ensure_workspace

__all__ = [
    "AtlasConfig",
    "WorkspacePaths",
    "detect_workspace_root",
    "ensure_workspace",
    "load_config",
    "load_or_create_config",
    "save_config",
]
