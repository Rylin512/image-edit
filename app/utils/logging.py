"""Rotating file logging with a console handler during development."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from app.utils.paths import app_data_dir

_configured = False


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logging once per process."""
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger()
    root.setLevel(level)
    formatter = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")

    try:
        log_dir = app_data_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
    except OSError:
        file_handler = None
    if file_handler is not None:
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    if not getattr(sys, "frozen", False):
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)
