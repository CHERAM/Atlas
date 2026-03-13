"""Shared Atlas exceptions."""


class AtlasError(Exception):
    """Base error for recoverable Atlas failures."""


class WorkspaceError(AtlasError):
    """Raised when workspace resolution or bootstrap fails."""


class ConfigError(AtlasError):
    """Raised when configuration cannot be loaded or saved."""
