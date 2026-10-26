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


def _require_image(image: QImage | None) -> QImage:
    if image is None or image.isNull():
        raise ValueError("图像操作没有返回有效图片")
    return image


class ImageOperationCommand(QUndoCommand):
    """Runs a pure image operation and restores the previous image on undo.

    Only the "before" snapshot is retained. The first redo can reuse a result
    that was already computed while validating the operation; later redos
    recompute it from the snapshot. Memory stays at roughly two images instead
    of three. Operations must therefore be deterministic and must not mutate
    external state.
    """

    def __init__(
        self,
        document: ImageDocument,
        text: str,
        operation: ImageOperation,
        parent: QUndoCommand | None = None,
        *,
        first_result: QImage | None = None,
    ) -> None:
        super().__init__(text, parent)
        self._document = document
        self._operation = operation
        self._before = document.image.copy()
        self._first_result = first_result

    def redo(self) -> None:
        if self._first_result is not None:
            result = self._first_result
            self._first_result = None
        else:
            result = self._operation(self._before.copy())
        self._document.replace_image(_require_image(result), modified=True)

    def undo(self) -> None:
        self._document.replace_image(self._before.copy(), modified=True)


def apply_image_operation(
    document: ImageDocument,
    undo_stack: QUndoStack,
    text: str,
    operation: ImageOperation,
) -> ImageOperationCommand | None:
    """Push ``operation`` onto the undo stack, or return None for an empty doc.

    The operation is validated before the command is pushed, so a failing
    operation cannot leave a broken entry on the stack.
    """
    if document.is_empty:
        return None

    first_result = _require_image(operation(document.image.copy()))
    command = ImageOperationCommand(
        document,
        text,
        operation,
        first_result=first_result,
    )
    undo_stack.push(command)
    return command
