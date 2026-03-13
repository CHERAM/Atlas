"""Models used by repo/sync services."""

from __future__ import annotations

from dataclasses import dataclass

from atlas.core.models import RepoConfig


@dataclass(slots=True)
class SyncResult:
    repo: RepoConfig
    action: str
    commit: str | None
    ok: bool
    message: str
