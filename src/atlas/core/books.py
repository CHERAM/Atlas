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
    """Discover book templates by scanning the built-in templates directory for frontmatter."""
    return _discover_templates(_template_source_dir())


def mode_mappings() -> list[tuple[str, str]]:
    """Return mode display names and mapped instruction files."""
    return [
        ("Atlas Prompt Creation", "Atlas-Prompt-Creation.md"),
        ("Atlas Java Test Creation", "Atlas-Java-Test-Creation.md"),
        ("Atlas API Contract", "Atlas-API-Contract.md"),
        ("Atlas Code Review", "Atlas-Code-Review.md"),
        ("Atlas Bug Fix", "Atlas-Bug-Fix.md"),
        ("Atlas Dev Workflow", "Atlas-Dev-Workflow.md"),
    ]


def _discover_templates(source_dir: Path) -> list[BookTemplate]:
    """Scan source_dir for .md files with valid name/purpose frontmatter."""
    templates: list[BookTemplate] = []
    for md_file in sorted(source_dir.glob("*.md")):
        meta = _parse_frontmatter(md_file.read_text(encoding="utf-8"))
        name = meta.get("name", "").strip()
        purpose = meta.get("purpose", "").strip()
        if name and purpose:
            templates.append(BookTemplate(name=name, filename=md_file.name, purpose=purpose))
    return templates


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Parse simple key: value YAML frontmatter delimited by --- lines."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    result: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


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
    numbered_modes = "\n".join(
        f"{index}. {name}" for index, (name, _) in enumerate(mode_mappings(), start=1)
    )
    return (
        "Book mode selection flow:\n"
        "1. On `activate`, `atlas activate`, or `activate atlas`, read `.github/atlas_mode.md`, show the Book Mode menu, and wait for selection by number or name.\n"
        "2. Confirm selected Book Mode and state: `Now referencing <filename> for guidance`.\n"
        "3. Show `Mode Strengths` and ask for execution style: `Continue in Auto or Manual mode?`\n"
        "4. If user types `capabilities` or `strengths`, show selected mode strengths again.\n\n"
        "Required activation response:\n"
        "- Immediately print the Book Mode menu exactly once and ask: `Select a mode by number or name.`\n"
        "- Do not stop at an activation acknowledgment.\n"
        "- Menu to show:\n"
        f"{numbered_modes}\n\n"
        "Execution style gating:\n"
        "- Never ask Auto/Manual before a Book Mode has been selected.\n"
        "- Auto/Manual is execution style for the selected Book Mode, not the menu itself.\n\n"
        "Activation command handling:\n"
        "- Treat `activate`, `atlas activate`, and `activate atlas` as chat-mode triggers.\n"
        "- Never execute those activation phrases as shell/terminal commands.\n\n"
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
        "- `switch`: clear current Book Mode and execution style, then return Book Mode menu.\n"
        "- `quit` or `exit`: deactivate mode system.\n"
        "- `activate <mode name>`: direct switch.\n"
        "- `atlas activate <mode name>`: direct switch alias.\n\n"
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
        "Treat `activate`, `atlas activate`, and `activate atlas` as conversational Atlas mode triggers.\n"
        "Do not execute these activation phrases as terminal commands.\n"
        "When activation or switch is triggered, immediately show the numbered Book Mode menu and ask for mode selection.\n"
        "Do not ask Auto/Manual until after Book Mode selection is complete.\n"
    )
    claude_body = (
        "Atlas contract source of truth: `.github/atlas/agent-contract.md`.\n"
        "Use that contract for mode selection and retrieval behavior.\n"
        "If shell execution is restricted, use Manual mode behavior.\n"
        "Treat `activate`, `atlas activate`, and `activate atlas` as conversational mode triggers, not shell commands.\n"
    )
    codex_body = (
        "Use `.github/atlas/agent-contract.md` as the canonical behavior contract.\n"
        "Follow mode flow and Auto/Manual retrieval rules from that contract.\n"
        "Fallback to Manual mode when execution tools are unavailable.\n"
        "Treat `activate`, `atlas activate`, and `activate atlas` as conversational mode triggers, not shell commands.\n"
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
