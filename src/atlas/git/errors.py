"""Repo/sync specific exceptions."""

from atlas.core.errors import AtlasError


class RepoError(AtlasError):
    """Base error for repository lifecycle and sync failures."""
