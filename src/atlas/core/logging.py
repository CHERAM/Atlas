"""Logging setup for Atlas CLI."""

from __future__ import annotations

import logging

DEFAULT_LOG_FORMAT = "%(levelname)s %(name)s: %(message)s"


def configure_logging(verbose: bool = False) -> None:
    """Configure root logging once for CLI execution."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format=DEFAULT_LOG_FORMAT)


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the given module name."""
    return logging.getLogger(name)
