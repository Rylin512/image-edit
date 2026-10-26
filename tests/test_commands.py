from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QImage, QUndoStack

from app.core.commands import apply_image_operation
from app.core.document import ImageDocument


def invert(image: QImage) -> QImage:
    image.invertPixels()
    return image


def inverted(color: QColor) -> QColor:
    return QColor(255 - color.red(), 255 - color.green(), 255 - color.blue())


def test_operation_applies_and_undoes(sample_image_path: Path) -> None:
    document = ImageDocument()
    assert document.load(sample_image_path)
    stack = QUndoStack()
    original = document.image.pixelColor(0, 0)

    assert apply_image_operation(document, stack, "反色", invert) is not None
    assert document.image.pixelColor(0, 0) == inverted(original)
    assert document.is_modified
    assert stack.canUndo()

    stack.undo()
    assert document.image.pixelColor(0, 0) == original
    assert stack.canRedo()

    stack.redo()
    assert document.image.pixelColor(0, 0) == inverted(original)


def test_operation_requires_an_open_image() -> None:
    document = ImageDocument()
    stack = QUndoStack()
    assert apply_image_operation(document, stack, "反色", invert) is None
    assert not stack.canUndo()


def test_operation_must_return_an_image(sample_image_path: Path) -> None:
    document = ImageDocument()
    assert document.load(sample_image_path)
    stack = QUndoStack()

    with pytest.raises(ValueError):
        apply_image_operation(document, stack, "坏操作", lambda image: QImage())

    assert not stack.canUndo()


def test_operation_runs_once_for_the_initial_application(sample_image_path: Path) -> None:
    document = ImageDocument()
    assert document.load(sample_image_path)
    stack = QUndoStack()
    calls = 0

    def operation(image: QImage) -> QImage:
        nonlocal calls
        calls += 1
        image.invertPixels()
        return image

    assert apply_image_operation(document, stack, "反色", operation) is not None
    assert calls == 1

    stack.undo()
    stack.redo()
    assert calls == 2
