"""Storage-specific errors."""

from atlas.core.errors import AtlasError


class StorageError(AtlasError):
    """Raised when metadata/vector persistence fails."""
