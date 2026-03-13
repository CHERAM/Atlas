"""Thin git CLI wrapper using subprocess."""

from __future__ import annotations

import subprocess
from pathlib import Path

from atlas.git.errors import RepoError


def _run_git(args: list[str], cwd: Path | None = None) -> str:
    cmd = ["git", *args]
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "unknown git error"
        where = f" (cwd={cwd})" if cwd else ""
        raise RepoError(f"git {' '.join(args)} failed{where}: {detail}")
    return proc.stdout.strip()


def clone_repo(url: str, branch: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    _run_git(["clone", "--branch", branch, "--single-branch", url, str(destination)])


def update_repo(path: Path, branch: str) -> None:
    if not (path / ".git").exists():
        raise RepoError(f"Repository path is not a git clone: {path}")

    _run_git(["fetch", "origin", branch], cwd=path)
    _run_git(["checkout", branch], cwd=path)
    _run_git(["pull", "--ff-only", "origin", branch], cwd=path)


def current_commit(path: Path) -> str:
    return _run_git(["rev-parse", "HEAD"], cwd=path)
