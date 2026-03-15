# Atlas — Claude Context

## Project Overview

Atlas is a local Python CLI that builds a cross-repository developer knowledge base for **architecture-first retrieval**. It helps developers and AI coding agents understand multiple repositories together by scanning, chunking, indexing, and ranking content — prioritizing architectural understanding over raw code snippets.

The primary output of Atlas is `.github/atlas/context.md` — an AI-ready context pack written for Copilot, Claude, and Codex agents.

**Package:** `atlas-cli` v0.1.0 | **Entry point:** `atlas.cli.app:app` | **Python 3.12+**

---

## Directory Structure

```
atlas/
├── src/atlas/              # Main package
│   ├── cli/                # Typer app + command modules (one file per command group)
│   │   └── commands/       # init, repo, sync, build, search, context, web, books, clean, reset
│   ├── core/               # Config, models, workspace paths, logging, error types, cleanup, books
│   ├── git/                # Repo cloning and syncing (GitPython-free; shells to git)
│   ├── scanner/            # File discovery, filtering, fingerprinting
│   ├── chunking/           # Document chunking strategies and models
│   ├── storage/            # SQLite metadata store, vector store abstraction, embedding pipeline
│   ├── search/             # Ranking, retrieval service, result formatting
│   ├── context/            # Context pack assembly, writing, service
│   ├── web/                # Web source registration, HTML ingestion
│   └── templates/books/    # Built-in instruction book templates (shipped as package data)
├── tests/                  # Unit tests (unittest, no pytest required)
├── docs/                   # Architecture and specification docs
├── AGENTS.md               # Multi-agent ownership rules (also Codex adapter)
├── pyproject.toml
└── atlas.yaml              # Generated per workspace; JSON stored with .yaml extension
```

> Each domain module has its own `models.py`, `errors.py`, and `__init__.py`. Sub-folder CLAUDE.md files will cover domain-specific detail.

---

## Key Configuration & Models

`atlas.yaml` is the workspace config file. It is **JSON serialized with a `.yaml` extension** (valid YAML subset). Loaded and validated via Pydantic.

Top-level config shape (`src/atlas/core/models.py`):

| Model | Purpose |
|---|---|
| `AtlasConfig` | Root config — owns all sub-configs |
| `WorkspaceConfig` | Directory paths (all relative to workspace root) |
| `RepoConfig` | A registered git repository |
| `WebSourceConfig` | A registered web/doc URL |
| `BuildConfig` | Sync-before-build flag, include/exclude globs, max file size |
| `EmbeddingConfig` | Provider, model name, vector dimensions |
| `SearchConfig` | Default `top_k` and `critical_k` |
| `WorkspacePaths` | Resolved `Path` objects for runtime use |

Default workspace paths (all relative to the CWD where `atlas init` was run):

```
.github/atlas/          # Context pack output + prompts
.atlas/books/           # Instruction book templates
.atlas-cache/           # All generated/cached data (gitignored)
.atlas-cache/repos/     # Cloned repositories
.atlas-cache/index/     # Vector index
.atlas-cache/web/       # Raw HTML from web sources
```

---

## Product Conventions

### Import Style

- Always use absolute imports from the package root: `from atlas.core.models import AtlasConfig`
- `from __future__ import annotations` at the top of every module
- Standard library → third-party → internal (blank line between each group)

### Naming Conventions

- **Files:** `snake_case.py`
- **Classes:** `PascalCase` — Pydantic models end in `Config`, `Model`, or the domain noun
- **Functions/methods:** `snake_case`
- **CLI commands:** `kebab-case` (Typer handles the conversion)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private helpers:** prefix with `_`

### File Organization

Each domain module follows this internal pattern:
```
models.py      # Pydantic data models for the domain
errors.py      # Domain-specific exceptions
service.py     # Business logic / orchestration
<noun>.py      # Focused single-responsibility helpers (e.g. discovery.py, ranking.py)
__init__.py    # Re-exports the public surface only
```

CLI commands live in `src/atlas/cli/commands/` — one file per command group, registered in `src/atlas/cli/app.py`.

### Error Handling

Each module defines its own exception class in `errors.py` inheriting from a base `AtlasError`. CLI commands catch domain errors and print user-friendly messages via `typer.echo`. Never let raw tracebacks reach the user from CLI paths.

---

## Development Workflow

### Install

```bash
python -m pip install -e .
atlas --version
```

### Running Locally (end-to-end)

```bash
atlas init
atlas repo add <git-url-or-local-path> --branch main
atlas sync
atlas build
atlas search "how request routing works"
atlas context "how request routing works"
# Output written to .github/atlas/context.md
```

### Testing

```bash
# Compile check
python -m compileall src tests

# Run all tests
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'

# Run a single test file
PYTHONPATH=src python -m unittest tests/test_search_ranking.py
```

Tests use the standard `unittest` module — no pytest dependency. Each meaningful module should have at least basic unit tests or a documented validation path.

### Adding a New CLI Command

1. Create `src/atlas/cli/commands/<name>.py` with a `typer.Typer()` app
2. Register it in `src/atlas/cli/app.py` via `app.add_typer(...)`
3. Keep command logic thin — delegate to a service in the relevant domain module

---

## Key Design Principles

- **Architecture-first retrieval** — search ranking prioritizes architectural docs and READMEs over raw code snippets. See `src/atlas/search/ranking.py`.
- **Composable services over tight coupling** — each domain exposes a service class; CLI commands wire them together.
- **No hidden global state** — config and workspace paths are passed explicitly, not read from globals or env vars.
- **Embedding behind an abstraction** — `EmbeddingConfig.provider` selects the provider. The MVP uses a `local-placeholder` that does not call any external API. Never hard-wire a real embedding provider.
- **Side effects localized** — file I/O and git operations are confined to specific modules (`git/`, `storage/`, `context/writer.py`).
- **Small, cohesive modules** — no god classes. If a module grows large, split by responsibility.
- **Type hints everywhere** — all function signatures must be typed.

---

## Extension Points

| What to extend | Where |
|---|---|
| Add a real embedding provider | `src/atlas/storage/embedding.py` — implement the provider interface, wire via `EmbeddingConfig.provider` |
| Add a new file type to scan | `src/atlas/scanner/filtering.py` |
| Add a new chunking strategy | `src/atlas/chunking/strategy.py` |
| Add a new context section | `src/atlas/context/assembler.py` |
| Add a new instruction book template | `src/atlas/templates/books/` — use `Atlas-Book-Template.md` as starter |
| Add a new CLI command group | `src/atlas/cli/commands/` + register in `app.py` |

---

## Multi-Agent Ownership

When multiple agents work in this repo simultaneously, each stays within its owned modules:

| Agent | Owns |
|---|---|
| CLI/Foundation | `src/atlas/cli/`, `src/atlas/core/` |
| Repo/Sync | `src/atlas/git/` |
| Indexing | `src/atlas/scanner/`, `src/atlas/chunking/` |
| Search/Storage | `src/atlas/storage/`, `src/atlas/search/` |
| Context | `src/atlas/context/` |
| Web | `src/atlas/web/` |

Cross-module changes must be proposed explicitly, not silently applied. See `AGENTS.md` for the full contract.
