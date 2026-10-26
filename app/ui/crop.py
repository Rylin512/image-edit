"""Interactive crop selection drawn over the canvas viewport."""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QPushButton, QWidget

if TYPE_CHECKING:
    from app.ui.canvas import CanvasView


class _Handle(Enum):
    NONE = auto()
    NEW = auto()
    MOVE = auto()
    TOP_LEFT = auto()
    TOP = auto()
    TOP_RIGHT = auto()
    RIGHT = auto()
    BOTTOM_RIGHT = auto()
    BOTTOM = auto()
    BOTTOM_LEFT = auto()
    LEFT = auto()


_CORNERS = (
    _Handle.TOP_LEFT,
    _Handle.TOP_RIGHT,
    _Handle.BOTTOM_LEFT,
    _Handle.BOTTOM_RIGHT,
)
_EDGES = (_Handle.TOP, _Handle.RIGHT, _Handle.BOTTOM, _Handle.LEFT)
_LEFT_HANDLES = (_Handle.TOP_LEFT, _Handle.LEFT, _Handle.BOTTOM_LEFT)
_RIGHT_HANDLES = (_Handle.TOP_RIGHT, _Handle.RIGHT, _Handle.BOTTOM_RIGHT)
_TOP_HANDLES = (_Handle.TOP_LEFT, _Handle.TOP, _Handle.TOP_RIGHT)
_BOTTOM_HANDLES = (_Handle.BOTTOM_LEFT, _Handle.BOTTOM, _Handle.BOTTOM_RIGHT)

_HIT_RADIUS = 9.0
_HANDLE_SIZE = 9.0
_MIN_SELECTION_PX = 24.0
_MASK_COLOR = QColor(6, 8, 12, 150)
_ACCENT = QColor("#5b8cff")


class CropOverlay(QWidget):
    """Free and aspect-locked crop selection over a :class:`CanvasView`."""

    accepted = Signal(QRect)
    cancelled = Signal()

    def __init__(self, parent: QWidget, canvas: CanvasView) -> None:
        super().__init__(parent)
        self._canvas = canvas
        self._aspect: float | None = None
        self._active = False
        self._selection = QRectF()
        self._selection_before_new = QRectF()
        self._mode = _Handle.NONE
        self._drag_origin = QPointF()
        self._drag_start = QRectF()
        self._drag_moved = False

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._cancel_button = QPushButton("取消", self)
        self._cancel_button.setObjectName("crop_cancel")
        self._cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_button.clicked.connect(self.cancel)

        self._apply_button = QPushButton("应用裁剪", self)
        self._apply_button.setObjectName("crop_apply")
        self._apply_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_button.setDefault(True)
        self._apply_button.clicked.connect(self.accept_crop)

        self.hide()

    # -- lifecycle -------------------------------------------------------
    @property
    def is_active(self) -> bool:
        return self._active

    def start(self, aspect_ratio: float | None = None) -> None:
        """Show the overlay with a full-image selection.

        ``aspect_ratio`` locks width / height; ``None`` allows free resizing.
        """
        if not self._canvas.has_image:
            return

        # Only a positive ratio may lock the selection. Treat anything else as
        # free cropping so an invalid value can never reach the ratio math.
        self._aspect = aspect_ratio if aspect_ratio and aspect_ratio > 0.0 else None
        self._selection = self._initial_selection(self._aspect)
        self._mode = _Handle.NONE
        self._drag_moved = False
        self._active = True
        self.setGeometry(self._canvas.viewport().rect())
        self.show()
        self.raise_()
        self._position_buttons()
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        self.update()

    def cancel(self) -> None:
        if not self._active:
            return
        self._active = False
        self.hide()
        self.cancelled.emit()

    def accept_crop(self) -> None:
        if not self._active:
            return
        rect = self.crop_rect()
        if rect.width() < 1 or rect.height() < 1:
            return
        self._active = False
        self.hide()
        self.accepted.emit(rect)

    def crop_rect(self) -> QRect:
        """The current selection in integer image pixels."""
        bounds = self._canvas.image_rect().toAlignedRect()
        rect = self._selection.toAlignedRect().intersected(bounds)
        return rect

    def _initial_selection(self, aspect_ratio: float | None) -> QRectF:
        bounds = self._canvas.image_rect()
        if bounds.isEmpty():
            return QRectF()
        if aspect_ratio is None or aspect_ratio <= 0.0:
            return QRectF(bounds)

        if bounds.width() / bounds.height() > aspect_ratio:
            height = bounds.height()
            width = height * aspect_ratio
        else:
            width = bounds.width()
            height = width / aspect_ratio
        return QRectF(
            bounds.center().x() - width / 2.0,
            bounds.center().y() - height / 2.0,
            width,
            height,
        )

    # -- geometry --------------------------------------------------------
    def _selection_view(self) -> QRectF:
        if self._selection.isEmpty():
            return QRectF()
        top_left = self._canvas.image_to_view(self._selection.topLeft())
        bottom_right = self._canvas.image_to_view(self._selection.bottomRight())
        return QRectF(top_left, bottom_right).normalized()

    def _image_view(self) -> QRectF:
        bounds = self._canvas.image_rect()
        top_left = self._canvas.image_to_view(bounds.topLeft())
        bottom_right = self._canvas.image_to_view(bounds.bottomRight())
        return QRectF(top_left, bottom_right).normalized()

    def _image_position(self, view_pos: QPointF, *, clamp: bool = False) -> QPointF:
        position = self._canvas.view_to_image(view_pos)
        if clamp:
            bounds = self._canvas.image_rect()
            position.setX(min(max(position.x(), bounds.left()), bounds.right()))
            position.setY(min(max(position.y(), bounds.top()), bounds.bottom()))
        return position

    def _minimum_size(self) -> float:
        zoom = self._canvas.zoom_factor
        if zoom <= 0.0:
            return 1.0
        return max(2.0, _MIN_SELECTION_PX / zoom)

    def _hit_test(self, pos: QPointF) -> _Handle:
        rect = self._selection_view()
        points = [
            (_Handle.TOP_LEFT, rect.topLeft()),
            (_Handle.TOP_RIGHT, rect.topRight()),
            (_Handle.BOTTOM_LEFT, rect.bottomLeft()),
            (_Handle.BOTTOM_RIGHT, rect.bottomRight()),
        ]
        if self._aspect is None:
            points.extend(
                [
                    (_Handle.TOP, QPointF(rect.center().x(), rect.top())),
                    (_Handle.RIGHT, QPointF(rect.right(), rect.center().y())),
                    (_Handle.BOTTOM, QPointF(rect.center().x(), rect.bottom())),
                    (_Handle.LEFT, QPointF(rect.left(), rect.center().y())),
                ]
            )

        for handle, point in points:
            if abs(pos.x() - point.x()) <= _HIT_RADIUS and abs(pos.y() - point.y()) <= _HIT_RADIUS:
                return handle
        if rect.contains(pos):
            return _Handle.MOVE
        if self._image_view().contains(pos):
            return _Handle.NEW
        return _Handle.NONE

    def _update_cursor(self, pos: QPointF) -> None:
        handle = self._hit_test(pos)
        cursors = {
            _Handle.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
            _Handle.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
            _Handle.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
            _Handle.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
            _Handle.TOP: Qt.CursorShape.SizeVerCursor,
            _Handle.BOTTOM: Qt.CursorShape.SizeVerCursor,
            _Handle.LEFT: Qt.CursorShape.SizeHorCursor,
            _Handle.RIGHT: Qt.CursorShape.SizeHorCursor,
            _Handle.MOVE: Qt.CursorShape.SizeAllCursor,
            _Handle.NEW: Qt.CursorShape.CrossCursor,
        }
        self.setCursor(cursors.get(handle, Qt.CursorShape.ArrowCursor))

    def _new_selection(self, origin: QPointF, pointer: QPointF) -> QRectF:
        bounds = self._canvas.image_rect()
        minimum = self._minimum_size()
        if self._aspect is None:
            rect = QRectF(origin, pointer).normalized().intersected(bounds)
            width = min(max(rect.width(), minimum), bounds.width())
            height = min(max(rect.height(), minimum), bounds.height())
            rect.setWidth(width)
            rect.setHeight(height)
            return self._keep_inside(rect, bounds)

        aspect = self._aspect
        direction_x = 1.0 if pointer.x() >= origin.x() else -1.0
        direction_y = 1.0 if pointer.y() >= origin.y() else -1.0
        max_width = bounds.right() - origin.x() if direction_x > 0 else origin.x() - bounds.left()
        max_height = bounds.bottom() - origin.y() if direction_y > 0 else origin.y() - bounds.top()
        max_width = max(0.0, min(max_width, max_height * aspect))
        desired = max(
            abs(pointer.x() - origin.x()),
            abs(pointer.y() - origin.y()) * aspect,
        )
        width = min(max(desired, min(minimum, max_width)), max_width)
        height = width / aspect
        return QRectF(
            origin,
            QPointF(origin.x() + direction_x * width, origin.y() + direction_y * height),
        ).normalized()

    def _resize_selection(self, pointer: QPointF) -> QRectF:
        start = self._drag_start
        bounds = self._canvas.image_rect()
        minimum = self._minimum_size()

        if self._aspect is None:
            left = start.left()
            top = start.top()
            right = start.right()
            bottom = start.bottom()
            if self._mode in _LEFT_HANDLES:
                left = max(bounds.left(), min(pointer.x(), right - minimum))
            if self._mode in _RIGHT_HANDLES:
                right = min(bounds.right(), max(pointer.x(), left + minimum))
            if self._mode in _TOP_HANDLES:
                top = max(bounds.top(), min(pointer.y(), bottom - minimum))
            if self._mode in _BOTTOM_HANDLES:
                bottom = min(bounds.bottom(), max(pointer.y(), top + minimum))
            return QRectF(QPointF(left, top), QPointF(right, bottom))

        anchors = {
            _Handle.TOP_LEFT: start.bottomRight(),
            _Handle.TOP_RIGHT: start.bottomLeft(),
            _Handle.BOTTOM_LEFT: start.topRight(),
            _Handle.BOTTOM_RIGHT: start.topLeft(),
        }
        anchor = anchors[self._mode]
        aspect = self._aspect
        direction_x = -1.0 if self._mode in (_Handle.TOP_LEFT, _Handle.BOTTOM_LEFT) else 1.0
        direction_y = -1.0 if self._mode in (_Handle.TOP_LEFT, _Handle.TOP_RIGHT) else 1.0
        max_width = anchor.x() - bounds.left() if direction_x < 0 else bounds.right() - anchor.x()
        max_height = anchor.y() - bounds.top() if direction_y < 0 else bounds.bottom() - anchor.y()
        max_width = max(0.0, min(max_width, max_height * aspect))
        desired = max(
            abs(pointer.x() - anchor.x()),
            abs(pointer.y() - anchor.y()) * aspect,
        )
        width = min(max(desired, min(minimum, max_width)), max_width)
        height = width / aspect
        return QRectF(
            anchor,
            QPointF(anchor.x() + direction_x * width, anchor.y() + direction_y * height),
        ).normalized()

    def _move_selection(self, pointer: QPointF) -> QRectF:
        delta = pointer - self._drag_origin
        rect = QRectF(self._drag_start).translated(delta)
        return self._keep_inside(rect, self._canvas.image_rect())

    @staticmethod
    def _keep_inside(rect: QRectF, bounds: QRectF) -> QRectF:
        rect = QRectF(rect)
        if rect.left() < bounds.left():
            rect.moveLeft(bounds.left())
        if rect.top() < bounds.top():
            rect.moveTop(bounds.top())
        if rect.right() > bounds.right():
            rect.moveRight(bounds.right())
        if rect.bottom() > bounds.bottom():
            rect.moveBottom(bounds.bottom())
        return rect

    def _nudge(self, dx: float, dy: float) -> None:
        bounds = self._canvas.image_rect()
        rect = self._selection.translated(dx, dy)
        self._selection = self._keep_inside(rect, bounds)
        self.update()

    # -- mouse and keyboard ---------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._active or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        self.setFocus()
        self._mode = self._hit_test(event.position())
        if self._mode is _Handle.NONE:
            event.accept()
            return

        self._drag_origin = self._image_position(event.position())
        self._drag_start = QRectF(self._selection)
        self._drag_moved = False
        if self._mode is _Handle.NEW:
            self._selection_before_new = QRectF(self._selection)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._active:
            super().mouseMoveEvent(event)
            return

        if self._mode is _Handle.NONE:
            self._update_cursor(event.position())
            event.accept()
            return

        pointer = self._image_position(event.position(), clamp=True)
        if self._mode is _Handle.NEW:
            self._selection = self._new_selection(self._drag_origin, pointer)
        elif self._mode is _Handle.MOVE:
            self._selection = self._move_selection(pointer)
        else:
            self._selection = self._resize_selection(pointer)
        self._drag_moved = True
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if not self._active:
            super().mouseReleaseEvent(event)
            return

        if self._mode is _Handle.NEW and not self._drag_moved:
            self._selection = self._selection_before_new
        self._mode = _Handle.NONE
        self._update_cursor(event.position())
        self.update()
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self._active and self._selection_view().contains(event.position()):
            self.accept_crop()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not self._active:
            super().keyPressEvent(event)
            return

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept_crop()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.cancel()
            event.accept()
            return

        step = 10.0 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1.0
        offsets = {
            Qt.Key.Key_Left: (-step, 0.0),
            Qt.Key.Key_Right: (step, 0.0),
            Qt.Key.Key_Up: (0.0, -step),
            Qt.Key.Key_Down: (0.0, step),
        }
        if event.key() in offsets:
            self._nudge(*offsets[event.key()])
            event.accept()
            return
        super().keyPressEvent(event)

    def wheelEvent(self, event) -> None:
        # Cropping works at the fitted zoom; letting the wheel zoom here would
        # make the handles tiny and move the selection under the pointer.
        event.ignore()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_buttons()

    # -- painting --------------------------------------------------------
    def _position_buttons(self) -> None:
        margin = 18
        gap = 8
        for button in (self._cancel_button, self._apply_button):
            button.adjustSize()
        apply_size = self._apply_button.sizeHint()
        cancel_size = self._cancel_button.sizeHint()

        y = max(margin, self.height() - margin - apply_size.height())
        apply_x = max(margin, self.width() - margin - apply_size.width())
        cancel_x = max(margin, apply_x - gap - cancel_size.width())
        self._apply_button.setGeometry(apply_x, y, apply_size.width(), apply_size.height())
        self._cancel_button.setGeometry(cancel_x, y, cancel_size.width(), cancel_size.height())

    def paintEvent(self, event) -> None:
        if not self._active:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        widget = QRectF(self.rect())
        selection = self._selection_view()

        if selection.width() <= 0.0 or selection.height() <= 0.0:
            painter.fillRect(widget, _MASK_COLOR)
            return

        painter.fillRect(
            QRectF(
                widget.left(),
                widget.top(),
                widget.width(),
                max(0.0, selection.top() - widget.top()),
            ),
            _MASK_COLOR,
        )
        painter.fillRect(
            QRectF(
                widget.left(),
                selection.bottom(),
                widget.width(),
                max(0.0, widget.bottom() - selection.bottom()),
            ),
            _MASK_COLOR,
        )
        painter.fillRect(
            QRectF(
                widget.left(),
                selection.top(),
                max(0.0, selection.left() - widget.left()),
                selection.height(),
            ),
            _MASK_COLOR,
        )
        painter.fillRect(
            QRectF(
                selection.right(),
                selection.top(),
                max(0.0, widget.right() - selection.right()),
                selection.height(),
            ),
            _MASK_COLOR,
        )

        painter.setBrush(Qt.BrushStyle.NoBrush)
        border = QPen(QColor(244, 248, 255, 238), 1.6)
        border.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(border)
        painter.drawRect(selection)

        thirds = QPen(QColor(255, 255, 255, 52), 1.0)
        painter.setPen(thirds)
        for index in (1, 2):
            x = selection.left() + selection.width() * index / 3.0
            y = selection.top() + selection.height() * index / 3.0
            painter.drawLine(QPointF(x, selection.top()), QPointF(x, selection.bottom()))
            painter.drawLine(QPointF(selection.left(), y), QPointF(selection.right(), y))

        handle_points = [selection.topLeft(), selection.topRight()]
        handle_points += [selection.bottomLeft(), selection.bottomRight()]
        if self._aspect is None:
            handle_points += [
                QPointF(selection.center().x(), selection.top()),
                QPointF(selection.right(), selection.center().y()),
                QPointF(selection.center().x(), selection.bottom()),
                QPointF(selection.left(), selection.center().y()),
            ]
        half = _HANDLE_SIZE / 2.0
        painter.setPen(QPen(_ACCENT, 1.4))
        for point in handle_points:
            painter.setBrush(QColor("#f5f8ff"))
            painter.drawRoundedRect(
                QRectF(point.x() - half, point.y() - half, _HANDLE_SIZE, _HANDLE_SIZE),
                2.2,
                2.2,
            )

        self._draw_size_badge(painter, selection)
        self._draw_hint(painter, widget)

    def _draw_size_badge(self, painter: QPainter, selection: QRectF) -> None:
        rect = self.crop_rect()
        if rect.width() < 1 or rect.height() < 1:
            return
        if selection.width() < 110.0 or selection.height() < 64.0:
            return

        label = f"{rect.width()} × {rect.height()} px"
        font = QFont(self.font())
        font.setPointSizeF(9.0)
        font.setWeight(QFont.Weight.DemiBold)
        metrics = QFontMetricsF(font)
        badge = QRectF(
            selection.left() + 12.0,
            selection.top() + 12.0,
            metrics.horizontalAdvance(label) + 18.0,
            metrics.height() + 8.0,
        )
        if badge.right() > selection.right() - 8.0:
            badge.moveRight(selection.right() - 8.0)
        if badge.bottom() > selection.bottom() - 8.0:
            badge.moveBottom(selection.bottom() - 8.0)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(10, 13, 19, 205))
        painter.drawRoundedRect(badge, 7.0, 7.0)
        painter.setFont(font)
        painter.setPen(QColor("#eaf0ff"))
        painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, label)

    def _draw_hint(self, painter: QPainter, widget: QRectF) -> None:
        label = "拖动调整 · Enter 应用 · Esc 取消"
        font = QFont(self.font())
        font.setPointSizeF(9.0)
        metrics = QFontMetricsF(font)
        width = metrics.horizontalAdvance(label) + 24.0
        if width > widget.width() - 32.0:
            return
        badge = QRectF(
            widget.center().x() - width / 2.0,
            widget.top() + 14.0,
            width,
            metrics.height() + 9.0,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(10, 13, 19, 185))
        painter.drawRoundedRect(badge, 8.0, 8.0)
        painter.setFont(font)
        painter.setPen(QColor(206, 218, 240, 225))
        painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, label)
