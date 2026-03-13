# Atlas CLI Command Flows

This file explains what each CLI command does, which files it touches, and the exact code path involved.

## 1. `atlas init`

### Purpose
Creates the Atlas workspace structure in the current project and ensures `atlas.yaml` exists.

### Entry path
- `src/atlas/cli/app.py`
- `src/atlas/cli/commands/init.py:init_command`

### Code flow
1. Typer routes `atlas init` to `init_command`.
2. `init_command` resolves the target root path.
3. `load_or_create_config` in `src/atlas/core/config.py` either:
   - loads existing `atlas.yaml`, or
   - creates a default `AtlasConfig` and writes it.
4. `ensure_workspace` in `src/atlas/core/workspace.py` creates:
   - `.github/atlas/`
   - `.github/atlas/prompts/`
   - `.atlas/books/`
   - `.atlas-cache/`
   - `.atlas-cache/repos/`
   - `.atlas-cache/index/`
   - `.atlas-cache/web/`
5. `seed_default_templates` in `src/atlas/core/books.py` copies built-in task instruction templates from `src/atlas/templates/books/` into `.atlas/books/`.
6. `bootstrap_persona_activation` copies `.github/atlas_persona.md`, `.github/atlas-instruction.md`, and updates `.github/copilot-instructions.md` with the managed persona block.
7. If the config was newly created, `save_config` writes canonical defaults.
8. The command prints the initialized location and whether config was created or reused.

### Main code involved
- `src/atlas/core/config.py`
- `src/atlas/core/workspace.py`
- `src/atlas/core/models.py`

## 2. `atlas repo add <git-url>`

### Purpose
Registers a repository in `atlas.yaml` so Atlas knows it should later clone and index it.

### Entry path
- `src/atlas/cli/app.py`
- `src/atlas/cli/commands/repo.py:repo_add_command`

### Code flow
1. Typer routes the subcommand to `repo_add_command`.
2. `RepoService()` in `src/atlas/git/service.py` loads workspace context using `load_workspace_context`.
3. `load_workspace_context` in `src/atlas/git/manifest.py`:
   - finds the workspace root,
   - loads `atlas.yaml`,
   - ensures required directories exist.
4. `RepoService.add_repo`:
   - derives a repo name from the URL with `derive_repo_name`,
   - checks for duplicate repo names and duplicate URLs,
   - computes the local clone path under `.atlas-cache/repos/<repo-name>`,
   - constructs a `RepoConfig`,
   - upserts it into config,
   - persists the updated manifest.
5. The command prints the repo name, URL, branch, and local path.

### Main code involved
- `src/atlas/git/service.py`
- `src/atlas/git/manifest.py`
- `src/atlas/core/config.py`

## 3. `atlas repo list`

### Purpose
Shows all registered repositories from `atlas.yaml`.

### Entry path
- `src/atlas/cli/commands/repo.py:repo_list_command`

### Code flow
1. `RepoService.list_repos()` returns `config.repos`.
2. The CLI prints one line per repo with name, branch, local path, URL, and enabled state.

### Main code involved
- `src/atlas/git/service.py`
- `src/atlas/core/models.py`

## 4. `atlas repo remove <name>`

### Purpose
Removes a repo from Atlas manifest, and optionally deletes the local clone.

### Entry path
- `src/atlas/cli/commands/repo.py:repo_remove_command`

### Code flow
1. `RepoService.remove_repo` removes the named repo from config using `remove_repo` in `manifest.py`.
2. The updated config is persisted to `atlas.yaml`.
3. If `--delete-local` is passed, the repo directory under `.atlas-cache/repos/` is deleted with `shutil.rmtree`.
4. The CLI prints whether only the manifest changed or both manifest and clone were removed.

### Main code involved
- `src/atlas/git/service.py`
- `src/atlas/git/manifest.py`

## 5. `atlas sync`

### Purpose
Makes local clones match the configured repositories and tracked branches.

### Entry path
- `src/atlas/cli/commands/sync.py:sync_command`

### Code flow
1. `sync_command` creates `RepoService()`.
2. `RepoService.sync` chooses either:
   - all registered repos, or
   - a single repo if `--name` is provided.
3. For each repo:
   - `local_repo_abs_path` resolves the absolute clone location.
   - If the directory already contains `.git`, `client.update_repo` runs:
     - `git fetch origin <branch>`
     - `git checkout <branch>`
     - `git pull --ff-only origin <branch>`
   - Otherwise `client.clone_repo` runs:
     - `git clone --branch <branch> --single-branch <url> <destination>`
   - `client.current_commit` runs `git rev-parse HEAD`.
   - `write_sync_state` records the latest commit in `.atlas-cache/index/repo-sync-state.json`.
4. Each per-repo operation returns a `SyncResult`.
5. The CLI prints `[OK]` or `[FAIL]` per repo and exits non-zero if any repo failed.

### Main code involved
- `src/atlas/git/service.py`
- `src/atlas/git/client.py`
- `src/atlas/git/manifest.py`

## 6. `atlas build`

### Purpose
Builds the knowledge base by discovering files, chunking them, embedding them, and storing metadata plus vectors.

### Entry path
- `src/atlas/cli/commands/build.py:build_command`

### Code flow
1. `build_command` optionally runs repo sync first unless `--no-sync` is passed.
2. `DiscoveryService.discover()` scans:
   - each enabled repo under `.atlas-cache/repos/`
   - raw HTML files under `.atlas-cache/web/`
3. During discovery, `filtering.py` decides whether to skip a file and classifies kept files.
4. Each kept file becomes a `DiscoveredFile` with metadata including:
   - source type
   - repo name
   - workspace-relative path
   - file type
   - content hash
   - fingerprint
5. `ChunkingStrategy.chunk_many()` converts discovered files to `IndexChunk` records.
   - Markdown and HTML are chunked section-by-section.
   - Other files are chunked line-by-line with overlap.
6. `WorkspaceStorage.from_workspace()` opens `.atlas-cache/index/atlas-metadata.db` and ensures schema exists.
7. `BuildStorageService.write_indexed_chunks()`:
   - starts a build run,
   - upserts repo metadata,
   - groups chunks by document,
   - upserts document rows,
   - replaces chunk rows,
   - deletes stale vectors for removed chunks,
   - embeds each chunk through `HashEmbeddingClient`,
   - upserts vectors into the `vectors` table,
   - marks the build run successful.
8. The CLI prints a build summary with run id, file count, chunk count, and skipped count.

### Main code involved
- `src/atlas/scanner/discovery.py`
- `src/atlas/scanner/filtering.py`
- `src/atlas/chunking/strategy.py`
- `src/atlas/storage/sqlite_store.py`
- `src/atlas/storage/pipeline.py`
- `src/atlas/storage/repositories.py`
- `src/atlas/storage/vector_store.py`
- `src/atlas/storage/embedding.py`

### Important note
`atlas build` is the command where most subsystems meet. If you want to understand Atlas as a product, this is the most important command to read deeply.

## 7. `atlas search "query"`

### Purpose
Retrieves ranked snippets from the built knowledge base.

### Entry path
- `src/atlas/cli/commands/search.py:search_command`

### Code flow
1. `SearchService.from_workspace()` opens the workspace SQLite storage.
2. `SearchService.search()`:
   - embeds the user query using `HashEmbeddingClient.embed_query`,
   - queries `LocalVectorStore.query()` for top vector hits,
   - optionally filters by `repo_name`,
   - fetches matching chunk metadata with `MetadataRepository.fetch_chunk_views`,
   - calls `rank_chunks` to apply Atlas ranking policy.
3. `rank_chunks` in `src/atlas/search/ranking.py` boosts:
   - architecture docs,
   - README files,
   - config wiring files,
   - chunks with section context.
4. `categorize_chunk` labels each result as `architecture`, `integration`, `interface`, `execution`, or `supporting`.
5. `format_search_results` renders the results for terminal output.
6. The service closes the SQLite connection.

### Main code involved
- `src/atlas/search/service.py`
- `src/atlas/search/ranking.py`
- `src/atlas/search/formatter.py`
- `src/atlas/storage/vector_store.py`
- `src/atlas/storage/repositories.py`

## 8. `atlas context "query"`

### Purpose
Runs retrieval and writes an AI-ready context pack to `.github/atlas/context.md`.

### Entry path
- `src/atlas/cli/commands/context.py:context_command`

### Code flow
1. `context_command` runs the same retrieval path as `search` via `SearchService.search()`.
2. The returned `SearchResult` list is passed to `ContextService.generate_from_results()`.
3. `ContextService`:
   - loads workspace/config,
   - ensures output directories exist,
   - uses `ContextAssembler` to build a structured `ContextPack`.
4. `ContextAssembler.assemble()`:
   - deduplicates repetitive results,
   - splits them into critical and supporting snippets,
   - derives relevant repositories,
   - writes a short architecture overview,
   - creates cross-repo notes,
   - generates a suggested AI handoff prompt.
5. `ContextWriter.write()` serializes the pack into markdown at `.github/atlas/context.md`.
6. The CLI prints the output path.

### Main code involved
- `src/atlas/context/service.py`
- `src/atlas/context/assembler.py`
- `src/atlas/context/writer.py`
- `src/atlas/search/service.py`

## 9. `atlas clean --cache`

### Purpose
Removes only the `.atlas-cache/` directory (repos, index, and web cache).

### Entry path
- `src/atlas/cli/commands/clean.py:clean_command`

### Code flow
1. The command requires `--cache` and prompts for confirmation unless `--force` is set.
2. `remove_cache_only` resolves workspace paths and deletes `.atlas-cache/` if present.
3. The CLI prints removed paths or a no-op message.

### Main code involved
- `src/atlas/core/cleanup.py`
- `src/atlas/cli/commands/clean.py`

## 10. `atlas reset --hard`

### Purpose
Hard reset of the workspace by deleting `.atlas-cache/`, `.github/atlas/`, `.atlas/books/`, and `atlas.yaml`.

### Entry path
- `src/atlas/cli/commands/reset.py:reset_command`

### Code flow
1. The command requires `--hard` and prompts for confirmation unless `--force` is set.
2. `remove_hard_reset` resolves workspace paths and deletes the cache dir, GitHub atlas dir, books dir, and config file if present.
3. The CLI prints removed paths or a no-op message.

### Main code involved
- `src/atlas/core/cleanup.py`
- `src/atlas/cli/commands/reset.py`

## 11. `atlas web add/list/remove/ingest`

### Purpose
Registers documentation URLs and stores one-time raw HTML snapshots for indexing.

### Entry path
- `src/atlas/cli/commands/web.py`

### Code flow for `atlas web add <url>`
1. `WebRegistryService` loads `atlas.yaml`.
2. `add_source()` validates the URL, derives a source id if needed, appends a `WebSourceConfig`, and saves config.
3. If `--ingest-now` is passed, `WebIngestionService.ingest_source()` fetches HTML immediately.

### Code flow for `atlas web ingest`
1. `WebIngestionService` loads registered sources via `WebRegistryService`.
2. `UrllibHtmlFetcher.fetch_html()` retrieves raw HTML.
3. The service writes:
   - timestamped HTML snapshot,
   - `latest.html`,
   - `index.json` with ingest metadata.
4. Those files live under `.atlas-cache/web/<source-id>/`.
5. Later, `atlas build` discovers those HTML files and indexes them like any other source.

### Main code involved
- `src/atlas/web/registry.py`
- `src/atlas/web/ingest.py`
- `src/atlas/web/models.py`

## 12. `atlas books list/pull`

### Purpose
Manages reusable task instruction markdown templates in `.atlas/books/` and copies them into `.github/` destinations.

### Entry path
- `src/atlas/cli/commands/books.py`

### Code flow for `atlas books list`
1. `list_templates()` ensures the workspace and books source folder exist.
2. `seed_default_templates()` writes/refreshes built-in template files.
3. CLI prints one line per template: name, filename, purpose.

### Code flow for `atlas books pull`
1. Requires exactly one selection mode:
   - `--name <template>`, or
   - `--all`
2. `pull_templates()` resolves destination scope:
   - current workspace `.github/` by default,
   - each registered local repo `.github/` with `--all-repos`.
3. Files are copied from `.atlas/books/` to target `.github/` directories (overwrite by default).
4. If `atlas_persona.md` is selected (or `--all`), Atlas refreshes `.github/atlas-instruction.md` and writes/updates `.github/copilot-instructions.md` with a managed persona-activation block.
5. Managed block enforces post-selection mode choice:
   - Auto mode: Copilot runs `atlas search` + `atlas context` and answers from `.github/atlas/context.md`.
   - Manual mode: user runs those commands and confirms context readiness; Copilot answers from context without command execution.
6. CLI prints copied count and paths.

### Main code involved
- `src/atlas/core/books.py`
- `src/atlas/cli/commands/books.py`

## 13. End-to-End Example Using Your Workflow

For this workflow:

```bash
atlas init
atlas repo add <repo1-url>
atlas repo add <repo2-url>
atlas sync
atlas build
atlas search "architecture and integration"
atlas context "architecture and integration"
```

the code path is:

1. `init` creates the workspace and config.
2. `repo add` appends two `RepoConfig` entries into `atlas.yaml`.
3. `sync` clones or updates both repositories under `.atlas-cache/repos/`.
4. `build` scans those clones, turns files into chunks, embeds them, and writes metadata plus vectors into SQLite.
5. `search` embeds the query, looks up similar chunks, re-ranks them with architecture-first boosts, and prints results.
6. `context` reuses the same ranked search results and writes a curated markdown artifact for AI handoff.

## 13. Recommended Reading Order For A First Pass

1. `src/atlas/cli/app.py`
2. `src/atlas/cli/commands/init.py`
3. `src/atlas/cli/commands/repo.py`
4. `src/atlas/cli/commands/build.py`
5. `src/atlas/git/service.py`
6. `src/atlas/scanner/discovery.py`
7. `src/atlas/chunking/strategy.py`
8. `src/atlas/storage/pipeline.py`
9. `src/atlas/search/service.py`
10. `src/atlas/context/service.py`
