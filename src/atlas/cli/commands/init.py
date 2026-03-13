"""Implementation of `atlas init`."""

from __future__ import annotations

from pathlib import Path

import typer

from atlas.core.books import bootstrap_mode_activation, seed_default_templates
from atlas.core.config import load_or_create_config, save_config
from atlas.core.errors import AtlasError
from atlas.core.workspace import ensure_workspace


def init_command(
    path: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
) -> None:
    """Initialize Atlas workspace folders and atlas.yaml in a project directory."""
    root = path.resolve()

    try:
        config_path = root / "atlas.yaml"
        config, created = load_or_create_config(config_path)
        paths = ensure_workspace(root, config)
        seeded = seed_default_templates(paths.books_dir)
        mode_written = bootstrap_mode_activation(root, paths.books_dir)

        # Backfill config with canonical relative defaults when first created.
        if created:
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
