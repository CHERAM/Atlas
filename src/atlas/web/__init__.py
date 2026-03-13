"""Web source registration and ingestion services for Atlas."""

from atlas.web.ingest import HtmlFetcher, UrllibHtmlFetcher, WebIngestionService
from atlas.web.models import IngestResult, RegisteredWebSource
from atlas.web.registry import WebRegistryService

__all__ = [
    "HtmlFetcher",
    "IngestResult",
    "RegisteredWebSource",
    "UrllibHtmlFetcher",
    "WebIngestionService",
    "WebRegistryService",
]
