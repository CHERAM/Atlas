"""Path filtering and file classification helpers for scanner."""

from __future__ import annotations

from pathlib import Path

from atlas.scanner.models import FileType

IGNORED_DIR_NAMES: set[str] = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "target",
    ".next",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".venv",
    "venv",
    ".eggs",
}

IGNORED_FILE_NAMES: set[str] = {
    ".ds_store",
    "thumbs.db",
}

IGNORED_SUFFIXES: set[str] = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".jar",
    ".war",
    ".mp3",
    ".mp4",
    ".mov",
    ".avi",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".pyc",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".bin",
    ".o",
    ".a",
    ".class",
    ".min.js",
    ".min.css",
    ".map",
    ".lock",
}

MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdx"}
HTML_SUFFIXES = {".html", ".htm"}
CONFIG_SUFFIXES = {
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".env",
    ".properties",
    ".xml",
}
CODE_SUFFIXES = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".kt",
    ".go",
    ".rs",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".scala",
    ".sql",
    ".sh",
    ".bash",
    ".zsh",
    ".ps1",
    ".dockerfile",
}


def should_skip_path(path: Path) -> bool:
    """Return True when a path is clearly not useful for Atlas indexing."""
    name = path.name.lower()
    if name in IGNORED_FILE_NAMES:
        return True

    if any(part.lower() in IGNORED_DIR_NAMES for part in path.parts):
        return True

    suffix = path.suffix.lower()
    if suffix in IGNORED_SUFFIXES:
        return True

    # Handle multi-extension generated assets like *.min.js
    if any(name.endswith(sfx) for sfx in IGNORED_SUFFIXES if sfx.startswith(".")):
        return True

    return False


def is_binary_file(path: Path, probe_bytes: int = 8192) -> bool:
    """Heuristic binary detection by probing initial bytes."""
    try:
        data = path.read_bytes()[:probe_bytes]
    except OSError:
        return True

    if not data:
        return False

    if b"\x00" in data:
        return True

    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        non_text = sum(byte < 9 or (13 < byte < 32) for byte in data)
        return (non_text / len(data)) > 0.20

    return False


def classify_file_type(path: Path) -> FileType | None:
    """Classify file type for chunking strategy and ranking hints."""
    name = path.name.lower()
    suffix = path.suffix.lower()

    if name.startswith("readme") or suffix in MARKDOWN_SUFFIXES:
        return "markdown"
    if suffix in HTML_SUFFIXES:
        return "html"
    if suffix in CONFIG_SUFFIXES or name in {"dockerfile", "makefile"}:
        return "config"
    if suffix in CODE_SUFFIXES:
        return "code"

    # Keep plain text candidates for architecture docs without extension.
    if suffix == "" and name in {"readme", "changelog", "license", "contributing"}:
        return "markdown"

    if suffix in {".txt", ".rst"}:
        return "text"

    return None


def language_hint(path: Path, file_type: FileType) -> str | None:
    """Return lightweight language/file hint used by downstream ranking."""
    if file_type == "markdown":
        return "markdown"
    if file_type == "html":
        return "html"
    if file_type == "config":
        return path.suffix.lower().lstrip(".") or path.name.lower()
    if file_type == "code":
        return path.suffix.lower().lstrip(".")
    if file_type == "text":
        return "text"
    return None
