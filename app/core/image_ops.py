"""Pure image operations shared by menu actions and crop tooling.

Keeping these functions free of widgets and document state makes them easy to
test and lets any new feature reuse them through ``MainWindow.apply_operation``.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QImage, QTransform


def _require_image(image: QImage) -> QImage:
    if image.isNull():
        raise ValueError("图像操作需要一张有效图片")
    return image


def _rotated(image: QImage, degrees: int) -> QImage:
    """Rotate by a multiple of 90 degrees without resampling the pixels."""
    _require_image(image)
    return image.transformed(
        QTransform().rotate(degrees),
        Qt.TransformationMode.FastTransformation,
    )


def rotate_left(image: QImage) -> QImage:
    """Rotate the image 90 degrees counter-clockwise."""
    return _rotated(image, -90)


def rotate_right(image: QImage) -> QImage:
    """Rotate the image 90 degrees clockwise."""
    return _rotated(image, 90)


def rotate_180(image: QImage) -> QImage:
    """Rotate the image by a half turn."""
    return _rotated(image, 180)


def _flipped(image: QImage, horizontal: bool, vertical: bool) -> QImage:
    _require_image(image)
    return image.transformed(
        QTransform().scale(-1 if horizontal else 1, -1 if vertical else 1),
        Qt.TransformationMode.FastTransformation,
    )


def flip_horizontal(image: QImage) -> QImage:
    """Mirror the image left-to-right."""
    return _flipped(image, horizontal=True, vertical=False)


def flip_vertical(image: QImage) -> QImage:
    """Mirror the image top-to-bottom."""
    return _flipped(image, horizontal=False, vertical=True)


def crop_image(image: QImage, rect: QRect) -> QImage:
    """Return the part of ``image`` inside ``rect``.

    The rectangle is normalised and clipped to the image bounds so a selection
    that rounds a fraction of a pixel outside the image still works.
    """
    _require_image(image)
    target = rect.normalized().intersected(image.rect())
    if target.isEmpty():
        raise ValueError("裁剪区域超出图像范围")
    return image.copy(target)
