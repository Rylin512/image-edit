"""The image document shared by the canvas, commands and the main window."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage

logger = logging.getLogger(__name__)


class ImageDocument(QObject):
    """An image plus its file path and modified state.

    The document never mutates the image in place. Commands receive a copy and
    hand back a new image, which keeps undo snapshots valid.
    """

    imageChanged = Signal()
    pathChanged = Signal(object)
    modifiedChanged = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._image = QImage()
        self._path: Path | None = None
        self._modified = False

    @property
    def image(self) -> QImage:
        return self._image

    @property
    def path(self) -> Path | None:
        return self._path

    @property
    def is_empty(self) -> bool:
        return self._image.isNull()

    @property
    def is_modified(self) -> bool:
        return self._modified

    @property
    def display_name(self) -> str:
        return self._path.name if self._path is not None else "未命名"

    def load(self, path: str | Path) -> bool:
        """Load an image from disk, leaving the document untouched on failure."""
        target = Path(path)
        image = QImage()
        if not image.load(str(target)):
            logger.warning("Could not load image: %s", target)
            return False

        self._set_path(target)
        self._set_image(image)
        self.set_modified(False)
        logger.info("Loaded image: %s (%d x %d)", target, image.width(), image.height())
        return True

    def replace_image(self, image: QImage, *, modified: bool = True) -> None:
        """Replace the image, for example from an undo command."""
        if image.isNull():
            raise ValueError("Cannot replace the document with an empty image")
        self._set_image(image)
        self.set_modified(modified)

    def save(self, path: str | Path | None = None) -> bool:
        """Write the current image to ``path`` (or the current path)."""
        if self._image.isNull():
            return False

        target = Path(path) if path is not None else self._path
        if target is None:
            return False
        if not self._image.save(str(target)):
            logger.warning("Could not save image: %s", target)
            return False

        self._set_path(target)
        self.set_modified(False)
        logger.info("Saved image: %s", target)
        return True

    def set_modified(self, modified: bool) -> None:
        if self._modified == modified:
            return
        self._modified = modified
        self.modifiedChanged.emit(modified)

    def _set_image(self, image: QImage) -> None:
        self._image = image
        self.imageChanged.emit()

    def _set_path(self, path: Path | None) -> None:
        if self._path == path:
            return
        self._path = path
        self.pathChanged.emit(path)
