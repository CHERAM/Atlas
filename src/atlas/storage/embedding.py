"""Embedding client boundary and local development implementation."""

from __future__ import annotations

import hashlib
import math
from typing import Protocol


class EmbeddingClient(Protocol):
    """Embedding interface used by build/search services."""

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""

    def embed_query(self, text: str) -> list[float]:
        """Embed a query string."""

    def dimension(self) -> int:
        """Return vector dimensionality."""

    def provider_name(self) -> str:
        """Provider identifier."""

    def model_name(self) -> str:
        """Model identifier."""


class HashEmbeddingClient:
    """Deterministic local embedding for MVP development/testing.

    This is intentionally simple and must remain behind the EmbeddingClient interface.
    """

    def __init__(self, dim: int = 384):
        self._dim = dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def dimension(self) -> int:
        return self._dim

    def provider_name(self) -> str:
        return "local"

    def model_name(self) -> str:
        return "hash-embedding-v1"

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        if not text:
            return vec

        tokens = text.lower().split()
        for tok in tokens:
            digest = hashlib.sha256(tok.encode("utf-8")).digest()
            for i in range(0, len(digest), 4):
                idx = int.from_bytes(digest[i : i + 2], "big") % self._dim
                sign = 1.0 if digest[i + 2] % 2 == 0 else -1.0
                magnitude = (digest[i + 3] / 255.0) + 0.1
                vec[idx] += sign * magnitude

        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0:
            return vec
        return [v / norm for v in vec]
