"""Shared data models for Atlas configuration and workspace paths."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic import field_validator


class WorkspaceConfig(BaseModel):
    github_dir: str = ".github/atlas"
    prompts_dir: str = ".github/atlas/prompts"
    books_dir: str = ".atlas/books"
    cache_dir: str = ".atlas-cache"
    repos_dir: str = ".atlas-cache/repos"
    index_dir: str = ".atlas-cache/index"
    web_dir: str = ".atlas-cache/web"


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


class AgentsConfig(BaseModel):
    selected: list[Literal["copilot", "claude", "codex"]] = Field(
        default_factory=lambda: ["copilot", "claude", "codex"]
    )

    @field_validator("selected", mode="before")
    @classmethod
    def normalize_selected(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                normalized.append(item)  # let pydantic raise a clear validation error
                continue
            lowered = item.strip().lower()
            if lowered and lowered not in seen:
                normalized.append(lowered)
                seen.add(lowered)
        return normalized


class AtlasConfig(BaseModel):
    version: int = 1
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    repos: list[RepoConfig] = Field(default_factory=list)
    web_sources: list[WebSourceConfig] = Field(default_factory=list)
    build: BuildConfig = Field(default_factory=BuildConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)


class WorkspacePaths(BaseModel):
    root: Path
    github_dir: Path
    prompts_dir: Path
    books_dir: Path
    cache_dir: Path
    repos_dir: Path
    index_dir: Path
    web_dir: Path
    config_path: Path
