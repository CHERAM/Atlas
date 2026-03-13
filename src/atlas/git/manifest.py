"""Manifest and sync state persistence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from atlas.core.config import load_config, save_config
from atlas.core.models import AtlasConfig, RepoConfig, WorkspacePaths
from atlas.core.workspace import detect_workspace_root, ensure_workspace
from atlas.git.errors import RepoError

SYNC_STATE_FILENAME = "repo-sync-state.json"


@dataclass(slots=True)
class RepoSyncState:
    repo_name: str
    branch: str
    local_path: str
    last_commit: str
    last_synced_at: str


@dataclass(slots=True)
class WorkspaceContext:
    root: Path
    config: AtlasConfig
    paths: WorkspacePaths


def load_workspace_context(start: Path | None = None) -> WorkspaceContext:
    root = detect_workspace_root(start)
    config_path = root / "atlas.yaml"
    if not config_path.exists():
        raise RepoError("atlas.yaml not found. Run `atlas init` in your project first.")

    config = load_config(config_path)
    paths = ensure_workspace(root, config)
    return WorkspaceContext(root=root, config=config, paths=paths)


def derive_repo_name(git_url: str) -> str:
    trimmed = git_url.rstrip("/")
    tail = trimmed.split(":")[-1] if ":" in trimmed and "/" not in trimmed.split(":")[-1] else trimmed
    name = Path(tail).name
    if name.endswith(".git"):
        name = name[:-4]
    if not name:
        raise RepoError(f"Could not derive repository name from URL: {git_url}")
    return name


def build_local_repo_relative_path(config: AtlasConfig, name: str) -> str:
    return (Path(config.workspace.repos_dir) / name).as_posix()


def find_repo(config: AtlasConfig, name: str) -> RepoConfig | None:
    for repo in config.repos:
        if repo.name == name:
            return repo
    return None


def upsert_repo(config: AtlasConfig, repo: RepoConfig) -> AtlasConfig:
    repos: list[RepoConfig] = [r for r in config.repos if r.name != repo.name]
    repos.append(repo)
    config.repos = sorted(repos, key=lambda r: r.name)
    return config


def remove_repo(config: AtlasConfig, name: str) -> tuple[AtlasConfig, RepoConfig | None]:
    removed: RepoConfig | None = None
    remaining: list[RepoConfig] = []
    for repo in config.repos:
        if repo.name == name:
            removed = repo
            continue
        remaining.append(repo)
    config.repos = remaining
    return config, removed


def save_manifest(context: WorkspaceContext) -> None:
    save_config(context.paths.config_path, context.config)


def sync_state_path(paths: WorkspacePaths) -> Path:
    return paths.index_dir / SYNC_STATE_FILENAME


def load_sync_states(paths: WorkspacePaths) -> dict[str, RepoSyncState]:
    state_file = sync_state_path(paths)
    if not state_file.exists():
        return {}

    try:
        raw = json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RepoError(f"Invalid sync state file: {state_file}") from exc

    result: dict[str, RepoSyncState] = {}
    for repo_name, item in raw.items():
        result[repo_name] = RepoSyncState(
            repo_name=repo_name,
            branch=item["branch"],
            local_path=item["local_path"],
            last_commit=item["last_commit"],
            last_synced_at=item["last_synced_at"],
        )
    return result


def write_sync_state(
    paths: WorkspacePaths,
    repo_name: str,
    branch: str,
    local_path: str,
    commit: str,
) -> None:
    states = load_sync_states(paths)
    states[repo_name] = RepoSyncState(
        repo_name=repo_name,
        branch=branch,
        local_path=local_path,
        last_commit=commit,
        last_synced_at=datetime.now(UTC).isoformat(),
    )
    payload = {name: asdict(state) for name, state in states.items()}
    sync_state_path(paths).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def local_repo_abs_path(root: Path, repo: RepoConfig) -> Path:
    candidate = Path(repo.local_path)
    return candidate if candidate.is_absolute() else (root / candidate)
