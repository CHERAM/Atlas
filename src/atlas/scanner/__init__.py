"""Scanner package for discovering indexable Atlas inputs.

Keep package import lightweight: avoid importing runtime-heavy modules at import time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["DiscoveryService", "DiscoveredFile", "ScanResult"]

if TYPE_CHECKING:
    from atlas.scanner.discovery import DiscoveryService
    from atlas.scanner.models import DiscoveredFile, ScanResult


def __getattr__(name: str) -> Any:
    if name == "DiscoveryService":
        from atlas.scanner.discovery import DiscoveryService

        return DiscoveryService
    if name in {"DiscoveredFile", "ScanResult"}:
        from atlas.scanner.models import DiscoveredFile, ScanResult

        return {"DiscoveredFile": DiscoveredFile, "ScanResult": ScanResult}[name]
    raise AttributeError(name)
