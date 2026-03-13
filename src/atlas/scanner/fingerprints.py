"""Hash and fingerprint helpers for incremental indexing."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class FileFingerprint:
    content_hash: str
    fingerprint: str
    size_bytes: int
    mtime_ns: int


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def hash_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(chunk_size)
            if not block:
                break
            hasher.update(block)
    return hasher.hexdigest()


def fingerprint_file(path: Path) -> FileFingerprint:
    stat = path.stat()
    content_hash = hash_file(path)
    # Include path-independent content hash + mutable file metadata for incremental checks.
    stamp = f"{content_hash}:{stat.st_size}:{stat.st_mtime_ns}".encode("utf-8")
    fingerprint = sha256_bytes(stamp)
    return FileFingerprint(
        content_hash=content_hash,
        fingerprint=fingerprint,
        size_bytes=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
    )
