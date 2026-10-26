"""Filesystem locations that work both from source and in a frozen build."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths


def app_data_dir() -> Path:
    """Return the per-user writable directory for logs and local state."""
    location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    path = Path(location) if location else Path.home() / ".image-edit"
    path.mkdir(parents=True, exist_ok=True)
    return path


def resource_path(*parts: str) -> Path:
    """Resolve a bundled resource, including inside a PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parents[2]
    return base.joinpath(*parts)
