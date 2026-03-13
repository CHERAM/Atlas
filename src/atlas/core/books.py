"""Books template catalog and distribution helpers."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from atlas.core.config import load_config
from atlas.core.errors import AtlasError
from atlas.core.workspace import detect_workspace_root, ensure_workspace

MODE_START_MARKER = "<!-- ATLAS:MODE_START -->"
MODE_END_MARKER = "<!-- ATLAS:MODE_END -->"
MODE_FILENAME = "atlas_mode.md"
INSTRUCTION_FILENAME = "atlas-instruction.md"
CONTRACT_FILENAME = "agent-contract.md"
COPILOT_INSTRUCTIONS_FILENAME = "copilot-instructions.md"
CLAUDE_FILENAME = "CLAUDE.md"
AGENTS_FILENAME = "AGENTS.md"
COPILOT_START_MARKER = "<!-- ATLAS:COPILOT_START -->"
COPILOT_END_MARKER = "<!-- ATLAS:COPILOT_END -->"
CLAUDE_START_MARKER = "<!-- ATLAS:CLAUDE_START -->"
CLAUDE_END_MARKER = "<!-- ATLAS:CLAUDE_END -->"
AGENTS_START_MARKER = "<!-- ATLAS:AGENTS_START -->"
AGENTS_END_MARKER = "<!-- ATLAS:AGENTS_END -->"


class BooksError(AtlasError):
    """Raised when books template operations fail."""


@dataclass(frozen=True, slots=True)
class BookTemplate:
    name: str
    filename: str
    purpose: str


@dataclass(frozen=True, slots=True)
class PullSummary:
    copied_files: list[Path]
    target_dirs: list[Path]


def default_templates() -> list[BookTemplate]:
    """Return Atlas book template metadata."""
    return [
        BookTemplate(
            name="prompt-creation",
            filename="Atlas-Prompt-Creation.md",
            purpose="Guide for crafting high-quality prompts with clear scope and constraints.",
        ),
        BookTemplate(
            name="java-test-creation",
            filename="Atlas-Java-Test-Creation.md",
            purpose="Playbook for adding reliable JUnit/integration tests for Java services.",
        ),
        BookTemplate(
            name="api-contract",
            filename="Atlas-API-Contract.md",
            purpose="Checklist for designing or updating API contracts safely.",
        ),
        BookTemplate(
            name="code-review",
            filename="Atlas-Code-Review.md",
            purpose="Structured review guide for finding functional and maintainability risks.",
        ),
        BookTemplate(
            name="bug-fix",
            filename="Atlas-Bug-Fix.md",
            purpose="Execution framework for diagnosing and validating production bug fixes.",
        ),
        BookTemplate(
            name="atlas-mode",
            filename=MODE_FILENAME,
            purpose="Mode selection menu and mode-to-file mapping for Copilot.",
        ),
        BookTemplate(
            name="atlas-instruction",
            filename=INSTRUCTION_FILENAME,
            purpose="Atlas command overview and Copilot operation guide.",
        ),
        BookTemplate(
            name="atlas-agent-contract",
            filename=CONTRACT_FILENAME,
            purpose="Canonical multi-agent contract for mode flow and retrieval behavior.",
        ),
    ]


def mode_mappings() -> list[tuple[str, str]]:
    """Return mode display names and mapped instruction files."""
    return [
        ("Atlas Prompt Creation", "Atlas-Prompt-Creation.md"),
        ("Atlas Java Test Creation", "Atlas-Java-Test-Creation.md"),
        ("Atlas API Contract", "Atlas-API-Contract.md"),
        ("Atlas Code Review", "Atlas-Code-Review.md"),
        ("Atlas Bug Fix", "Atlas-Bug-Fix.md"),
    ]


def bootstrap_mode_activation(workspace_root: Path, books_dir: Path) -> list[Path]:
    """Copy mode/contract files and inject managed adapter instructions."""
    github_dir = workspace_root / ".github"
    github_dir.mkdir(parents=True, exist_ok=True)
    mode_source = books_dir / MODE_FILENAME
    if not mode_source.exists():
        raise BooksError(f"Mode template missing in workspace books: {mode_source}")
    mode_target = github_dir / MODE_FILENAME
    shutil.copy2(mode_source, mode_target)

    instruction_source = books_dir / INSTRUCTION_FILENAME
    if not instruction_source.exists():
        raise BooksError(f"Instruction template missing in workspace books: {instruction_source}")
    instruction_target = github_dir / INSTRUCTION_FILENAME
    shutil.copy2(instruction_source, instruction_target)

    contract_target = _copy_agent_contract(books_dir=books_dir, target_github_dir=github_dir)
    adapter_targets = _upsert_agent_adapters(target_github_dir=github_dir)
    return [mode_target, instruction_target, contract_target, *adapter_targets]


def seed_default_templates(books_dir: Path) -> list[Path]:
    """Copy built-in templates into the workspace books directory."""
    source_dir = _template_source_dir()
    books_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for template in default_templates():
        source = source_dir / template.filename
        if not source.exists():
            raise BooksError(f"Template file missing in Atlas repo: {source}")
        destination = books_dir / template.filename
        shutil.copy2(source, destination)
        written.append(destination)

    return written


def list_templates(start_path: Path | None = None) -> list[BookTemplate]:
    """List templates after ensuring workspace copies are present."""
    _, books_dir = _load_paths(start_path)
    seed_default_templates(books_dir)
    return default_templates()


def pull_templates(
    *,
    name: str | None,
    pull_all: bool,
    all_repos: bool,
    start_path: Path | None = None,
) -> PullSummary:
    """Copy one or all templates to destination `.github/` directories."""
    if bool(name) == bool(pull_all):
        raise BooksError("Specify exactly one of --name <template> or --all.")

    root, books_dir = _load_paths(start_path)
    seed_default_templates(books_dir)
    available = {template.name: template for template in default_templates()}

    if pull_all:
        selected = list(available.values())
    else:
        assert name is not None
        normalized = name.strip().lower().replace(" ", "-")
        template = available.get(normalized)
        if not template:
            valid = ", ".join(sorted(available.keys()))
            raise BooksError(f"Unknown template '{name}'. Available: {valid}")
        selected = [template]

    include_mode_bootstrap = any(template.filename == MODE_FILENAME for template in selected)
    include_contract_refresh = include_mode_bootstrap or any(
        template.filename == CONTRACT_FILENAME for template in selected
    )

    target_dirs = _resolve_targets(root=root, all_repos=all_repos)
    copied_files: list[Path] = []
    errors: list[str] = []

    for target_dir in target_dirs:
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            errors.append(f"{target_dir}: {exc}")
            continue

        for template in selected:
            if template.filename == CONTRACT_FILENAME:
                continue
            source = books_dir / template.filename
            destination = target_dir / template.filename
            try:
                shutil.copy2(source, destination)
                copied_files.append(destination)
            except OSError as exc:
                errors.append(f"{destination}: {exc}")

        if include_contract_refresh:
            try:
                copied_files.append(
                    _copy_agent_contract(books_dir=books_dir, target_github_dir=target_dir)
                )
            except OSError as exc:
                errors.append(f"{target_dir / 'atlas' / CONTRACT_FILENAME}: {exc}")

        if include_mode_bootstrap:
            try:
                copied_files.extend(_upsert_agent_adapters(target_dir))
            except OSError as exc:
                errors.append(f"{target_dir / COPILOT_INSTRUCTIONS_FILENAME}: {exc}")

    if errors:
        raise BooksError("Completed with copy failures. " + "; ".join(errors))

    return PullSummary(copied_files=copied_files, target_dirs=target_dirs)


def _render_contract_body() -> str:
    mapping_lines = "\n".join(f"- {name} -> .github/{filename}" for name, filename in mode_mappings())
    return (
        "Mode selection flow:\n"
        "1. On `activate`, read `.github/atlas_mode.md`, show mode menu, and wait for selection by number or name.\n"
        "2. Confirm selected mode and state: `Now referencing <filename> for guidance`.\n"
        "3. Show `Mode Strengths` and ask: `Continue in Auto or Manual mode?`\n"
        "4. If user types `capabilities` or `strengths`, show selected mode strengths again.\n\n"
        "Auto mode:\n"
        "- Ask for prompt.\n"
        "- Run `atlas search \"<prompt>\"`.\n"
        "- Run `atlas context \"<prompt>\"`.\n"
        "- Answer using `.github/atlas/context.md`.\n\n"
        "Manual mode:\n"
        "- Ask user to run `atlas search \"<prompt>\"` and `atlas context \"<prompt>\"`.\n"
        "- Ask `Context ready? yes/no`.\n"
        "- If yes, answer using `.github/atlas/context.md`.\n"
        "- Do not execute shell commands in Manual mode.\n\n"
        "Persistent commands:\n"
        "- `switch`: return mode menu.\n"
        "- `quit` or `exit`: deactivate mode system.\n"
        "- `activate <mode name>`: direct switch.\n\n"
        "Mode mapping:\n"
        f"{mapping_lines}\n\n"
        "Fallback:\n"
        "- If command execution is unavailable or fails, explain the issue and suggest recovery (`atlas init`, `atlas build`, then retry).\n"
    )


def _upsert_agent_adapters(target_github_dir: Path) -> list[Path]:
    contract_ref = ".github/atlas/agent-contract.md"
    copilot_body = (
        "Follow the canonical Atlas agent contract at `.github/atlas/agent-contract.md`.\n"
        "When command execution is unavailable, automatically follow Manual mode from the contract.\n"
    )
    claude_body = (
        "Atlas contract source of truth: `.github/atlas/agent-contract.md`.\n"
        "Use that contract for mode selection and retrieval behavior.\n"
        "If shell execution is restricted, use Manual mode behavior.\n"
    )
    codex_body = (
        "Use `.github/atlas/agent-contract.md` as the canonical behavior contract.\n"
        "Follow mode flow and Auto/Manual retrieval rules from that contract.\n"
        "Fallback to Manual mode when execution tools are unavailable.\n"
    )

    copilot_path = _upsert_managed_block(
        path=target_github_dir / COPILOT_INSTRUCTIONS_FILENAME,
        start_marker=COPILOT_START_MARKER,
        end_marker=COPILOT_END_MARKER,
        title="Atlas Copilot Adapter",
        body=copilot_body,
    )
    repo_root = target_github_dir.parent
    claude_path = _upsert_managed_block(
        path=repo_root / CLAUDE_FILENAME,
        start_marker=CLAUDE_START_MARKER,
        end_marker=CLAUDE_END_MARKER,
        title="Atlas Claude Adapter",
        body=claude_body,
    )
    agents_path = _upsert_managed_block(
        path=repo_root / AGENTS_FILENAME,
        start_marker=AGENTS_START_MARKER,
        end_marker=AGENTS_END_MARKER,
        title="Atlas Codex Adapter",
        body=codex_body,
    )
    _ = contract_ref  # avoid accidental removal from adapter templates if edited
    return [copilot_path, claude_path, agents_path]


def _upsert_managed_block(
    *,
    path: Path,
    start_marker: str,
    end_marker: str,
    title: str,
    body: str,
) -> Path:
    managed_block = f"{start_marker}\n## {title}\n{body}{end_marker}\n"
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    pattern = re.compile(rf"{re.escape(start_marker)}.*?{re.escape(end_marker)}\n?", re.DOTALL)
    if pattern.search(current):
        updated = pattern.sub(managed_block, current, count=1)
    elif current.strip():
        updated = current.rstrip() + "\n\n" + managed_block
    else:
        updated = managed_block
    path.write_text(updated, encoding="utf-8")
    return path


def _copy_agent_contract(*, books_dir: Path, target_github_dir: Path) -> Path:
    source = books_dir / CONTRACT_FILENAME
    if not source.exists():
        raise BooksError(f"Contract template missing in workspace books: {source}")
    contract_dir = target_github_dir / "atlas"
    contract_dir.mkdir(parents=True, exist_ok=True)
    target = contract_dir / CONTRACT_FILENAME
    header = (
        "# Atlas Agent Contract\n\n"
        "This is the canonical, tool-agnostic Atlas behavior contract for Copilot, Claude, and Codex.\n\n"
    )
    target.write_text(header + _render_contract_body(), encoding="utf-8")
    return target


def _template_source_dir() -> Path:
    source_dir = Path(__file__).resolve().parents[1] / "templates" / "books"
    if not source_dir.exists():
        raise BooksError(f"Atlas template source directory not found: {source_dir}")
    return source_dir


def _load_paths(start_path: Path | None) -> tuple[Path, Path]:
    root = detect_workspace_root(start_path)
    config_path = root / "atlas.yaml"
    if not config_path.exists():
        raise BooksError("atlas.yaml not found. Run `atlas init` in your project first.")

    config = load_config(config_path)
    paths = ensure_workspace(root, config)
    return root, paths.books_dir


def _resolve_targets(root: Path, all_repos: bool) -> list[Path]:
    if not all_repos:
        return [root / ".github"]

    config = load_config(root / "atlas.yaml")
    targets: list[Path] = []
    for repo in config.repos:
        local_path = Path(repo.local_path)
        repo_root = local_path if local_path.is_absolute() else (root / local_path)
        if not repo_root.exists():
            raise BooksError(f"Local repository path not found for '{repo.name}': {repo_root}")
        targets.append(repo_root / ".github")
    return targets
