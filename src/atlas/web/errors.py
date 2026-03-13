"""Web ingestion specific exceptions."""

from atlas.core.errors import AtlasError


class WebError(AtlasError):
    """Raised when web source registration or ingestion fails."""
