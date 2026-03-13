"""High-level repo lifecycle and sync operations."""

from __future__ import annotations

import shutil
from pathlib import Path

from atlas.core.models import RepoConfig
from atlas.git import client
from atlas.git.errors import RepoError
from atlas.git.manifest import (
    build_local_repo_relative_path,
    derive_repo_name,
    find_repo,
    load_workspace_context,
    local_repo_abs_path,
    remove_repo,
    save_manifest,
    upsert_repo,
    write_sync_state,
)
from atlas.git.models import SyncResult


class RepoService:
    """Service for repository registration and synchronization."""

    def __init__(self, start_path: Path | None = None):
        self.context = load_workspace_context(start_path)

    def add_repo(self, git_url: str, branch: str = "main", name: str | None = None) -> RepoConfig:
        repo_name = name or derive_repo_name(git_url)
        existing = find_repo(self.context.config, repo_name)
        if existing:
            raise RepoError(f"Repository already exists: {repo_name}")

        if any(repo.url == git_url for repo in self.context.config.repos):
            raise RepoError(f"Repository URL is already registered: {git_url}")

        local_path = build_local_repo_relative_path(self.context.config, repo_name)
        repo = RepoConfig(
            name=repo_name,
            url=git_url,
            branch=branch,
            local_path=local_path,
            enabled=True,
        )
        upsert_repo(self.context.config, repo)
        save_manifest(self.context)
        return repo

    def list_repos(self) -> list[RepoConfig]:
        return list(self.context.config.repos)

    def remove_repo(self, name: str, delete_local: bool = False) -> RepoConfig:
        _, removed = remove_repo(self.context.config, name)
        if not removed:
            raise RepoError(f"Repository not found: {name}")

        save_manifest(self.context)

        if delete_local:
            local_dir = local_repo_abs_path(self.context.root, removed)
            if local_dir.exists():
                shutil.rmtree(local_dir)

        return removed

    def sync(self, name: str | None = None) -> list[SyncResult]:
        repos = self.context.config.repos
        if name is not None:
            repos = [repo for repo in repos if repo.name == name]
            if not repos:
                raise RepoError(f"Repository not found: {name}")

        results: list[SyncResult] = []
        for repo in repos:
            local_dir = local_repo_abs_path(self.context.root, repo)
            try:
                if local_dir.exists() and (local_dir / ".git").exists():
                    client.update_repo(local_dir, repo.branch)
                    action = "pulled"
                elif local_dir.exists() and any(local_dir.iterdir()):
                    raise RepoError(
                        f"Local path exists and is not an empty git directory: {local_dir}"
                    )
                else:
                    client.clone_repo(repo.url, repo.branch, local_dir)
                    action = "cloned"

                commit = client.current_commit(local_dir)
                write_sync_state(
                    self.context.paths,
                    repo_name=repo.name,
                    branch=repo.branch,
                    local_path=repo.local_path,
                    commit=commit,
                )
                results.append(
                    SyncResult(
                        repo=repo,
                        action=action,
                        commit=commit,
                        ok=True,
                        message=f"{repo.name}: {action}",
                    )
                )
            except RepoError as exc:
                results.append(
                    SyncResult(
                        repo=repo,
                        action="failed",
                        commit=None,
                        ok=False,
                        message=str(exc),
                    )
                )

        return results
