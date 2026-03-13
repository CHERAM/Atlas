"""Context-pack generation for Atlas.

Keep package import lightweight: avoid importing runtime-heavy modules at import time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["ContextAssembler", "ContextPack", "ContextService", "ContextSnippet", "ContextWriter"]

if TYPE_CHECKING:
    from atlas.context.assembler import ContextAssembler
    from atlas.context.models import ContextPack, ContextSnippet
    from atlas.context.service import ContextService
    from atlas.context.writer import ContextWriter


def __getattr__(name: str) -> Any:
    if name == "ContextAssembler":
        from atlas.context.assembler import ContextAssembler

        return ContextAssembler
    if name == "ContextPack":
        from atlas.context.models import ContextPack

        return ContextPack
    if name == "ContextSnippet":
        from atlas.context.models import ContextSnippet

        return ContextSnippet
    if name == "ContextService":
        from atlas.context.service import ContextService

        return ContextService
    if name == "ContextWriter":
        from atlas.context.writer import ContextWriter

        return ContextWriter
    raise AttributeError(name)
