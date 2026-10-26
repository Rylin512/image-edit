"""The image document shared by the canvas, commands and the main window."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QIODevice, QObject, QSaveFile, Signal
from PySide6.QtGui import QImage, QImageReader

from app.utils.files import save_format_for_path

logger = logging.getLogger(__name__)

JPEG_QUALITY = 92


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
        """Load an image from disk, applying its EXIF orientation if present.

        The document is left untouched when reading fails.
        """
        target = Path(path)
        reader = QImageReader(str(target))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            logger.warning("Could not load image: %s (%s)", target, reader.errorString())
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
        """Atomically write the current image to ``path`` (or the current path)."""
        if self._image.isNull():
            return False

        target = Path(path) if path is not None else self._path
        if target is None:
            return False

        image_format = save_format_for_path(target)
        if image_format is None:
            logger.warning("Unsupported image format: %s", target)
            return False

        quality = JPEG_QUALITY if image_format in {"jpg", "jpeg"} else -1
        output = QSaveFile(str(target))
        if not output.open(QIODevice.OpenModeFlag.WriteOnly):
            logger.warning(
                "Could not open image for writing: %s (%s)", target, output.errorString()
            )
            return False

        if not self._image.save(output, image_format, quality):
            logger.warning("Could not save image: %s (%s)", target, output.errorString())
            output.cancelWriting()
            return False

        if not output.commit():
            logger.warning("Could not commit image: %s (%s)", target, output.errorString())
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
