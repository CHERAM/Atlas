"""Chunking package for transforming discovered files into index chunks."""

from atlas.chunking.models import IndexChunk
from atlas.chunking.strategy import ChunkingStrategy

__all__ = ["IndexChunk", "ChunkingStrategy"]
