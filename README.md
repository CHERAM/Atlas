# Atlas CLI

Atlas is a local Python CLI that builds a cross-repository developer knowledge base for architecture-first retrieval.

## What Atlas Does

Atlas helps you:
- register multiple git repositories
- sync local clones
- scan and chunk code/docs/config/html
- build a local metadata + vector index
- run ranked search
- generate AI-ready context in `.github/atlas/context.md`
- maintain reusable task instruction books in `.atlas/books`

## Requirements

- Python 3.12+
- `git` on PATH

## Install

From this repository root:

```bash
python -m pip install -e .
```

Verify:

```bash
atlas --version
atlas --help
```

## Quick Start

### 1) Initialize Atlas in a project folder

```bash
atlas init
```

This creates:
- `.github/atlas/`
- `.github/atlas/prompts/`
- `.atlas/books/`
- `.atlas-cache/`
- `.atlas-cache/repos/`
- `.atlas-cache/index/`
- `.atlas-cache/web/`
- `atlas.yaml`

### 2) Add repositories

```bash
atlas repo add <git-url-or-local-path> --branch main
atlas repo list
```

Remove a repo from manifest only:

```bash
atlas repo remove <repo-name>
```

Remove from manifest and delete local clone:

```bash
atlas repo remove <repo-name> --delete-local
```

### 3) Sync repositories

Sync all:

```bash
atlas sync
```

Sync one:

```bash
atlas sync --name <repo-name>
```

### 4) Build the index

By default, build syncs first:

```bash
atlas build
```

Skip sync if already up to date:

```bash
atlas build --no-sync
```

### 5) Search

```bash
atlas search "how request routing works"
```

Useful options:

```bash
atlas search "query" --top-k 20 --critical-k 5
atlas search "query" --repo <repo-name>
```

Search output includes:
- repository
- file path
- line range (when available)
- snippet
- score
- relevance reason

### 6) Generate AI context pack

```bash
atlas context "how request routing works"
```

Output file:
- `.github/atlas/context.md`

Useful options:

```bash
atlas context "query" --top-k 20
atlas context "query" --critical-k 3
atlas context "query" --repo <repo-name>
```

Context file sections:
- query
- relevant repositories
- architecture overview
- critical snippets
- supporting snippets
- cross-repo notes
- suggested prompt for AI agent usage

## Cleanup and Reset

Remove cache only:

```bash
atlas clean --cache
```

Hard reset (deletes cache, `.github/atlas/`, `.atlas/books/`, and `atlas.yaml`):

```bash
atlas reset --hard
```

Skip confirmation prompt:

```bash
atlas clean --cache --force
atlas reset --hard --force
```

## Web Source Registration & Ingestion

Register docs/wiki/web URL:

```bash
atlas web add https://example.com/docs --kind docs
```

Register and ingest immediately:

```bash
atlas web add https://example.com/docs --kind docs --ingest-now
```

List/remove sources:

```bash
atlas web list
atlas web remove <source-id>
```

One-time ingestion:

```bash
atlas web ingest --id <source-id>
atlas web ingest --all
```

Raw HTML storage:
- `.atlas-cache/web/<source-id>/<timestamp>.html`
- `.atlas-cache/web/<source-id>/latest.html`
- `.atlas-cache/web/<source-id>/index.json`

## Books Templates

Atlas keeps reusable task instruction templates in `.atlas/books` (source of truth), and can copy them into `.github/` for Copilot/agent workflows.
The built-in templates are stored in this Atlas repository at `src/atlas/templates/books/` and are copied into your workspace during `atlas init`.

List available templates:

```bash
atlas books list
```

Copy one template into current workspace `.github/`:

```bash
atlas books pull --name prompt-creation
```

Copy all templates into current workspace `.github/`:

```bash
atlas books pull --all
```

Copy all templates into every registered local repository clone `.github/`:

```bash
atlas books pull --all --all-repos
```

`atlas init` automatically bootstraps persona activation by creating/updating:
- `.github/atlas_persona.md`
- `.github/atlas-instruction.md`
- `.github/copilot-instructions.md` (managed persona block)

When `atlas_persona.md` is pulled later (or `--all` is used), Atlas updates the same managed block idempotently so newly added books can be refreshed into target repos.
Use `src/atlas/templates/books/Atlas-Book-Template.md` as the starter template for creating new book files.
Persona flow supports two retrieval modes after selection:
- `Auto`: Copilot runs `atlas search` then `atlas context`, then answers from `.github/atlas/context.md`.
- `Manual`: user runs those commands and confirms context is ready; Copilot then answers from `.github/atlas/context.md` without executing commands.

## Typical End-to-End Workflow

```bash
atlas init
atlas repo add <repo1-url>
atlas repo add <repo2-url>
atlas sync
atlas build
atlas search "architecture and integration"
atlas context "architecture and integration"
```

## Configuration (`atlas.yaml`)

`atlas.yaml` stores workspace paths, repos, web sources, and build/search settings.

Current implementation persists JSON-formatted content in `atlas.yaml` (valid YAML subset).

## Troubleshooting

If `atlas` command is not found:

```bash
python -m pip install -e .
```

If sync fails:
- ensure git URL/path is valid
- ensure you have permissions for private repos
- run `atlas repo list` to confirm repo name/branch

If search/context returns no results:
- run `atlas sync`
- run `atlas build`
- verify repos were indexed and not excluded by filters

## Development Validation

```bash
python -m compileall src tests
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
```
