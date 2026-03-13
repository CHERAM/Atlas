"""Web source registration service using atlas.yaml manifest."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from atlas.core.config import load_config, save_config
from atlas.core.models import WebSourceConfig
from atlas.core.workspace import detect_workspace_root, ensure_workspace, resolve_workspace_paths
from atlas.web.errors import WebError
from atlas.web.models import RegisteredWebSource

_SOURCE_ID_RE = re.compile(r"[^a-z0-9]+")


class WebRegistryService:
    """Manage web/doc/wiki source registration in `atlas.yaml`."""

    def __init__(self, start_path: Path | None = None):
        self.root = detect_workspace_root(start_path)
        self.config_path = self.root / "atlas.yaml"
        if not self.config_path.exists():
            raise WebError("atlas.yaml not found. Run `atlas init` first.")

        self.config = load_config(self.config_path)
        self.paths = resolve_workspace_paths(self.root, self.config)
        ensure_workspace(self.root, self.config)

    def add_source(self, url: str, kind: str = "docs", source_id: str | None = None) -> RegisteredWebSource:
        if not _looks_like_url(url):
            raise WebError(f"Invalid URL: {url}")

        if any(item.url == url for item in self.config.web_sources):
            raise WebError(f"Web source already registered for URL: {url}")

        sid = source_id or self._derive_source_id(url)
        if any(item.id == sid for item in self.config.web_sources):
            raise WebError(f"Web source id already exists: {sid}")

        item = WebSourceConfig(id=sid, url=url, kind=kind, enabled=True)
        self.config.web_sources.append(item)
        self.config.web_sources.sort(key=lambda entry: entry.id)
        save_config(self.config_path, self.config)

        return RegisteredWebSource(source_id=item.id, url=item.url, kind=item.kind, enabled=item.enabled)

    def list_sources(self, include_disabled: bool = True) -> list[RegisteredWebSource]:
        sources = [
            RegisteredWebSource(
                source_id=item.id,
                url=item.url,
                kind=item.kind,
                enabled=item.enabled,
            )
            for item in self.config.web_sources
        ]
        if include_disabled:
            return sources
        return [source for source in sources if source.enabled]

    def remove_source(self, source_id: str) -> RegisteredWebSource:
        removed: WebSourceConfig | None = None
        remaining: list[WebSourceConfig] = []

        for item in self.config.web_sources:
            if item.id == source_id:
                removed = item
            else:
                remaining.append(item)

        if removed is None:
            raise WebError(f"Web source not found: {source_id}")

        self.config.web_sources = remaining
        save_config(self.config_path, self.config)
        return RegisteredWebSource(
            source_id=removed.id,
            url=removed.url,
            kind=removed.kind,
            enabled=removed.enabled,
        )

    def get_source(self, source_id: str) -> RegisteredWebSource:
        for item in self.config.web_sources:
            if item.id == source_id:
                return RegisteredWebSource(
                    source_id=item.id,
                    url=item.url,
                    kind=item.kind,
                    enabled=item.enabled,
                )
        raise WebError(f"Web source not found: {source_id}")

    @staticmethod
    def _derive_source_id(url: str) -> str:
        parsed = urlparse(url)
        seed = f"{parsed.netloc}-{parsed.path}".strip("-") or "web-source"
        sid = _SOURCE_ID_RE.sub("-", seed.lower()).strip("-")
        return sid[:64] or "web-source"


def _looks_like_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
