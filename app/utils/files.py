"""File dialog filters and extension helpers."""

from __future__ import annotations

import re
from pathlib import Path

IMAGE_OPEN_FILTER = (
    "图片文件 (*.png *.jpg *.jpeg *.bmp *.webp *.gif *.tif *.tiff);;"
    "PNG 图片 (*.png);;JPEG 图片 (*.jpg *.jpeg);;WebP 图片 (*.webp);;所有文件 (*)"
)
IMAGE_SAVE_FILTER = (
    "PNG 图片 (*.png);;"
    "JPEG 图片 (*.jpg *.jpeg);;"
    "WebP 图片 (*.webp);;"
    "BMP 图片 (*.bmp);;"
    "TIFF 图片 (*.tif *.tiff)"
)

SUPPORTED_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tif", ".tiff"})

_SUFFIX_PATTERN = re.compile(r"\*(\.[0-9A-Za-z]+)")
_SAVE_FORMATS = {
    ".png": "png",
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".webp": "webp",
    ".bmp": "bmp",
    ".tif": "tiff",
    ".tiff": "tiff",
}


def suffix_from_filter(selected_filter: str) -> str:
    """Return the first extension named by a Qt name filter, defaulting to PNG."""
    match = _SUFFIX_PATTERN.search(selected_filter)
    return match.group(1).lower() if match else ".png"


def is_supported_image(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_SUFFIXES


def save_format_for_path(path: str | Path) -> str | None:
    """Return the Qt image format for a save path, or None if unsupported."""
    return _SAVE_FORMATS.get(Path(path).suffix.lower())
