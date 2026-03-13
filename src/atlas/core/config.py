"""Configuration loading and persistence helpers for atlas.yaml."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from atlas.core.errors import ConfigError
from atlas.core.models import AtlasConfig


def load_config(config_path: Path) -> AtlasConfig:
    """Load and validate Atlas config from `atlas.yaml`."""
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        raw_text = config_path.read_text(encoding="utf-8")
        raw: dict[str, Any] = json.loads(raw_text) if raw_text.strip() else {}
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Failed to parse config: {config_path}") from exc

    try:
        return AtlasConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"Invalid Atlas config in {config_path}") from exc


def save_config(config_path: Path, config: AtlasConfig) -> None:
    """Persist Atlas config to YAML."""
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = config.model_dump(mode="json")
        config_path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise ConfigError(f"Failed to write config at {config_path}") from exc


def load_or_create_config(config_path: Path) -> tuple[AtlasConfig, bool]:
    """Load existing config or create default config if missing.

    Returns `(config, created)`.
    """
    if config_path.exists():
        return load_config(config_path), False

    config = AtlasConfig()
    save_config(config_path, config)
    return config, True
