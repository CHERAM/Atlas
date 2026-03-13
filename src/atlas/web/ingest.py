"""One-time raw HTML ingestion plumbing for web sources."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from urllib.request import Request, urlopen

from atlas.web.models import IngestResult, RegisteredWebSource
from atlas.web.registry import WebRegistryService


class HtmlFetcher(Protocol):
    """Boundary for retrieving raw HTML from a source URL."""

    def fetch_html(self, url: str) -> str:
        """Fetch HTML text for a URL."""


class UrllibHtmlFetcher:
    """Default MVP HTML fetcher using urllib and no browser automation."""

    def __init__(self, timeout_seconds: int = 20):
        self.timeout_seconds = timeout_seconds

    def fetch_html(self, url: str) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": "atlas-mvp/0.1 (+https://local.atlas)",
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            payload = response.read()
        return payload.decode(charset, errors="replace")


class WebIngestionService:
    """Ingest registered web sources as raw HTML snapshots under `.codebuddy-cache/web/`."""

    def __init__(
        self,
        start_path: Path | None = None,
        fetcher: HtmlFetcher | None = None,
    ):
        self.registry = WebRegistryService(start_path=start_path)
        self.fetcher: HtmlFetcher = fetcher or UrllibHtmlFetcher()
        self.web_root = self.registry.paths.web_dir

    def ingest_source(self, source_id: str) -> IngestResult:
        source = self.registry.get_source(source_id)
        if not source.enabled:
            return IngestResult(
                source_id=source.source_id,
                url=source.url,
                ok=False,
                html_path=None,
                metadata_path=None,
                message="Source is disabled.",
            )

        return self._ingest(source)

    def ingest_all(self) -> list[IngestResult]:
        results: list[IngestResult] = []
        for source in self.registry.list_sources(include_disabled=False):
            results.append(self._ingest(source))
        return results

    def _ingest(self, source: RegisteredWebSource) -> IngestResult:
        source_dir = self.web_root / source.source_id
        source_dir.mkdir(parents=True, exist_ok=True)

        try:
            html = self.fetcher.fetch_html(source.url)
            timestamp = _now_stamp()
            html_path = source_dir / f"{timestamp}.html"
            latest_path = source_dir / "latest.html"
            metadata_path = source_dir / "index.json"

            html_path.write_text(html, encoding="utf-8")
            latest_path.write_text(html, encoding="utf-8")
            _append_ingest_metadata(metadata_path, source, html_path)

            return IngestResult(
                source_id=source.source_id,
                url=source.url,
                ok=True,
                html_path=html_path,
                metadata_path=metadata_path,
                message="Ingestion completed.",
            )
        except Exception as exc:
            return IngestResult(
                source_id=source.source_id,
                url=source.url,
                ok=False,
                html_path=None,
                metadata_path=None,
                message=f"Ingestion failed: {exc}",
            )


def _append_ingest_metadata(metadata_path: Path, source: RegisteredWebSource, html_path: Path) -> None:
    payload = {
        "source_id": source.source_id,
        "url": source.url,
        "kind": source.kind,
        "ingested_at": datetime.now(UTC).isoformat(),
        "html_path": html_path.name,
    }

    index_payload: dict
    if metadata_path.exists():
        try:
            index_payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            index_payload = {}
    else:
        index_payload = {}

    entries = index_payload.get("entries", [])
    if not isinstance(entries, list):
        entries = []
    entries.append(payload)

    # Keep latest record simple for future scanners/chunkers.
    index_payload = {
        "source": asdict(source),
        "latest": payload,
        "entries": entries,
    }
    metadata_path.write_text(json.dumps(index_payload, indent=2), encoding="utf-8")


def _now_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
