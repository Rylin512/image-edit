"""Undoable image operations.

Feature modules only need to provide a pure ``QImage -> QImage`` callable and
push it through :func:`apply_image_operation`; snapshotting and undo wiring are
handled here.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QImage, QUndoCommand, QUndoStack

from app.core.document import ImageDocument

ImageOperation = Callable[[QImage], QImage]


class ImageOperationCommand(QUndoCommand):
    """Runs a pure image operation and restores the previous image on undo.

    Only the "before" snapshot is retained. Redo recomputes the result from it,
    which keeps memory at roughly two images instead of three. Operations must
    therefore be deterministic and must not mutate external state.
    """

    def __init__(
        self,
        document: ImageDocument,
        text: str,
        operation: ImageOperation,
        parent: QUndoCommand | None = None,
    ) -> None:
        super().__init__(text, parent)
        self._document = document
        self._operation = operation
        self._before = document.image.copy()

    def redo(self) -> None:
        result = self._operation(self._before.copy())
        if result is None or result.isNull():
            raise ValueError("图像操作没有返回有效图片")
        self._document.replace_image(result, modified=True)

    def undo(self) -> None:
        self._document.replace_image(self._before.copy(), modified=True)


def apply_image_operation(
    document: ImageDocument,
    undo_stack: QUndoStack,
    text: str,
    operation: ImageOperation,
) -> ImageOperationCommand | None:
    """Push ``operation`` onto the undo stack, or return None for an empty doc."""
    if document.is_empty:
        return None
    command = ImageOperationCommand(document, text, operation)
    undo_stack.push(command)
    return command
