"""Shared data models for Atlas configuration and workspace paths."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class WorkspaceConfig(BaseModel):
    github_dir: str = ".github/atlas"
    prompts_dir: str = ".github/atlas/prompts"
    cache_dir: str = ".codebuddy-cache"
    repos_dir: str = ".codebuddy-cache/repos"
    index_dir: str = ".codebuddy-cache/index"
    web_dir: str = ".codebuddy-cache/web"


class RepoConfig(BaseModel):
    name: str
    url: str
    branch: str = "main"
    local_path: str
    enabled: bool = True


class WebSourceConfig(BaseModel):
    id: str
    url: str
    kind: str = "docs"
    enabled: bool = True


class BuildConfig(BaseModel):
    run_sync_by_default: bool = True
    include_globs: list[str] = Field(default_factory=list)
    exclude_globs: list[str] = Field(default_factory=list)
    max_file_bytes: int = 1_048_576


class EmbeddingConfig(BaseModel):
    provider: str = "local-placeholder"
    model: str = "mvp-default"
    dim: int = 384


class SearchConfig(BaseModel):
    top_k: int = 20
    critical_k: int = 5


class AtlasConfig(BaseModel):
    version: int = 1
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    repos: list[RepoConfig] = Field(default_factory=list)
    web_sources: list[WebSourceConfig] = Field(default_factory=list)
    build: BuildConfig = Field(default_factory=BuildConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)


class WorkspacePaths(BaseModel):
    root: Path
    github_dir: Path
    prompts_dir: Path
    cache_dir: Path
    repos_dir: Path
    index_dir: Path
    web_dir: Path
    config_path: Path
