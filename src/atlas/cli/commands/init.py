"""Implementation of `atlas init`."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from atlas.core.books import bootstrap_mode_activation, seed_default_templates
from atlas.core.config import load_or_create_config, save_config
from atlas.core.errors import AtlasError
from atlas.core.workspace import ensure_workspace


def init_command(
    path: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
    agents: str | None = typer.Option(
        None,
        "--agents",
        help="Comma-separated agents to configure: copilot, claude, codex.",
    ),
) -> None:
    """Initialize Atlas workspace folders and atlas.yaml in a project directory."""
    root = path.resolve()

    try:
        config_path = root / "atlas.yaml"
        config, created = load_or_create_config(config_path)
        original_agents = list(config.agents.selected)
        selected_agents = _resolve_selected_agents(
            agents_option=agents,
            existing=original_agents,
            created=created,
        )
        config.agents.selected = selected_agents
        paths = ensure_workspace(root, config)
        seeded = seed_default_templates(paths.books_dir)
        mode_written = bootstrap_mode_activation(
            root, paths.books_dir, selected_agents=selected_agents
        )

        if created or agents is not None:
            save_config(paths.config_path, config)

        typer.echo(f"Atlas initialized at {root}")
        if created:
            typer.echo(f"Created {paths.config_path}")
        else:
            typer.echo(f"Reused existing {paths.config_path}")
        typer.echo(f"Seeded {len(seeded)} books templates in {paths.books_dir}")
        typer.echo(
            "Configured mode activation files: " + ", ".join(str(path) for path in mode_written)
        )
    except AtlasError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _resolve_selected_agents(
    *,
    agents_option: str | None,
    existing: list[str],
    created: bool,
) -> list[str]:
    if agents_option is not None:
        return _parse_agents_csv(agents_option)
    if not created and existing:
        return existing
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise AtlasError(
            "No agents selected. Run `atlas init --agents copilot,claude,codex` (choose one or more)."
        )
    response = typer.prompt(
        "Select agents to configure (comma-separated: copilot,claude,codex)",
        default="copilot,claude,codex",
    )
    return _parse_agents_csv(response)


def _parse_agents_csv(raw: str) -> list[str]:
    allowed = {"copilot", "claude", "codex"}
    tokens = [piece.strip().lower() for piece in raw.split(",") if piece.strip()]
    deduped: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token not in seen:
            deduped.append(token)
            seen.add(token)
    if not deduped:
        raise AtlasError("No agents selected. Choose one or more of: copilot, claude, codex.")
    invalid = [token for token in deduped if token not in allowed]
    if invalid:
        raise AtlasError(
            f"Invalid agent(s): {', '.join(invalid)}. Allowed values: copilot, claude, codex."
        )
    return deduped
