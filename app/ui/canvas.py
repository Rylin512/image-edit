"""Zoomable image canvas built on QGraphicsView.

The view only changes its transform when zooming, so window resizing and
panning never rescale the full image on the CPU. Interaction follows common
image-viewer conventions: the wheel zooms under the cursor and dragging with
the left or middle mouse button pans.

Zoom steps and newly opened images use short easing animations. They only
animate the view transform and item opacity, so the pixel data is never
re-rendered by Python.
"""

from __future__ import annotations

import math

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QPoint,
    QPointF,
    QRectF,
    Qt,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QTransform,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QPushButton,
)


class CanvasView(QGraphicsView):
    """Displays one image with smooth zoom, pan and cursor coordinates."""

    zoomChanged = Signal(float)  # percentage, 0 when no image is shown
    cursorPositionChanged = Signal(object)  # QPointF in image pixels or None
    openRequested = Signal()

    MIN_ZOOM = 0.01
    MAX_ZOOM = 32.0
    ZOOM_STEP = 1.2  # per mouse-wheel notch
    ZOOM_ANIMATION_MS = 160
    WHEEL_ANIMATION_MS = 90
    IMAGE_FADE_MS = 180
    DROP_FADE_MS = 150

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item = QGraphicsPixmapItem()
        self._pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self._scene.addItem(self._pixmap_item)

        self.setFrameShape(QFrame.Shape.NoFrame)
        # The camera lives in the pixmap item's transform, not in the view.
        # QGraphicsView's scrollbars can only move in whole pixels, which made
        # animated zoom visibly jitter; keeping them off lets us position the
        # image with sub-pixel precision and a constant viewport size.
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QColor("#0d0f14"))
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.viewport().setMouseTracking(True)

        self._zoom = 0.0
        self._center = QPointF()  # image coordinate shown at the viewport center
        self._zoom_start = 0.0
        self._zoom_target = 0.0
        self._zoom_anchor = QPointF()  # viewport position kept fixed while zooming
        self._zoom_anchor_image = QPointF()  # matching image coordinate
        self._zoom_start_center = QPointF()
        self._zoom_target_center = QPointF()
        self._zoom_blend_center = False
        self._fit_mode = True
        self._panning = False
        self._pan_origin = QPointF()
        self._drop_active = False
        self._drop_alpha = 0.0
        self._grid_brush = self._make_grid_brush()

        self._zoom_animation = QVariantAnimation(self)
        self._zoom_animation.setStartValue(0.0)
        self._zoom_animation.setEndValue(1.0)
        self._zoom_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._zoom_animation.valueChanged.connect(self._on_zoom_tick)
        self._zoom_animation.finished.connect(self._on_zoom_finished)

        self._opacity_animation = QVariantAnimation(self)
        self._opacity_animation.setDuration(self.IMAGE_FADE_MS)
        self._opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._opacity_animation.valueChanged.connect(self._on_opacity_tick)

        self._drop_animation = QVariantAnimation(self)
        self._drop_animation.setDuration(self.DROP_FADE_MS)
        self._drop_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._drop_animation.valueChanged.connect(self._on_drop_tick)

        self._open_button = QPushButton("打开图片", self.viewport())
        self._open_button.setObjectName("empty_open_button")
        self._open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_button.clicked.connect(self.openRequested.emit)
        self._update_open_button()

    @property
    def zoom_factor(self) -> float:
        return self._zoom

    @property
    def is_zooming(self) -> bool:
        return self._zoom_animation.state() == QAbstractAnimation.State.Running

    @property
    def has_image(self) -> bool:
        return not self._pixmap_item.pixmap().isNull()

    def view_to_image(self, view_pos: QPointF | QPoint) -> QPointF:
        """Map a viewport position to image pixels, keeping sub-pixel accuracy."""
        if self._zoom <= 0.0:
            return QPointF()
        return self._center + (QPointF(view_pos) - self._viewport_center()) / self._zoom

    def image_to_view(self, image_pos: QPointF | QPoint) -> QPointF:
        """Map a position in image pixels to viewport coordinates."""
        if not self.has_image:
            return QPointF()
        return QPointF(self.mapFromScene(self._pixmap_item.mapToScene(QPointF(image_pos))))

    def image_rect(self) -> QRectF:
        """The displayed image bounds in image pixels."""
        return QRectF(self._pixmap_item.boundingRect())

    def advance_zoom_animation(self, fraction: float) -> None:
        """Jump within a running zoom animation (tests, screenshots)."""
        if not self.is_zooming:
            return
        duration = self._zoom_animation.duration()
        self._zoom_animation.setCurrentTime(int(duration * max(0.0, min(1.0, fraction))))

    # -- image lifecycle -------------------------------------------------
    def set_image(self, image: QImage, *, reset_view: bool = False) -> None:
        """Show ``image``.

        ``reset_view`` fits the image to the window (use it when opening a new
        file). Without it the current zoom is kept, which is what edit commands
        want.
        """
        if image.isNull():
            self.clear_image()
            return

        pixmap = QPixmap.fromImage(image)
        if pixmap.isNull():
            self.clear_image()
            return

        had_image = self.has_image
        self._opacity_animation.stop()
        self._pixmap_item.setOpacity(1.0)
        self._pixmap_item.setPixmap(pixmap)
        self._scene.setSceneRect(QRectF(pixmap.rect()))

        if reset_view or not had_image or self._fit_mode or self._zoom <= 0.0:
            self._fit_now()
        else:
            self._apply_camera(self._zoom, self._center)

        self._update_open_button()
        self._update_cursor()
        self.viewport().update()

    def clear_image(self) -> None:
        self._zoom_animation.stop()
        self._opacity_animation.stop()
        self._pixmap_item.setPixmap(QPixmap())
        self._pixmap_item.setOpacity(1.0)
        self._pixmap_item.setTransform(QTransform())
        self._scene.setSceneRect(QRectF())
        self._zoom = 0.0
        self._center = QPointF()
        self._zoom_start = 0.0
        self._zoom_target = 0.0
        self._zoom_anchor = QPointF()
        self._zoom_anchor_image = QPointF()
        self._zoom_start_center = QPointF()
        self._zoom_target_center = QPointF()
        self._zoom_blend_center = False
        self._fit_mode = True
        self._update_open_button()
        self._update_cursor()
        self.viewport().update()
        self.zoomChanged.emit(0.0)

    def animate_image_in(self) -> None:
        """Fade the current image in; used when a file is opened."""
        if not self.has_image:
            return
        if not self.isVisible():
            self._pixmap_item.setOpacity(1.0)
            return

        self._opacity_animation.stop()
        self._pixmap_item.setOpacity(0.0)
        self._opacity_animation.setStartValue(0.0)
        self._opacity_animation.setEndValue(1.0)
        self._opacity_animation.setDuration(self.IMAGE_FADE_MS)
        self._opacity_animation.start()

    # -- zoom ------------------------------------------------------------
    def reset_view(self) -> None:
        self._fit_mode = True
        self._fit_now()

    def fit_to_window(self) -> None:
        """Animate to a centered fit; never upscale images smaller than the view."""
        scale = self._fit_scale()
        if scale is None:
            return
        self._fit_mode = True
        self._animate_zoom_to(
            scale,
            self._viewport_center(),
            self.ZOOM_ANIMATION_MS,
            fit_mode=True,
            anchor_image=self._image_center(),
        )

    def actual_size(self) -> None:
        if not self.has_image:
            return
        self._animate_zoom_to(
            1.0,
            self._viewport_center(),
            self.ZOOM_ANIMATION_MS,
            fit_mode=False,
        )

    def zoom_in(self) -> None:
        self.zoom_by(self.ZOOM_STEP)

    def zoom_out(self) -> None:
        self.zoom_by(1 / self.ZOOM_STEP)

    def zoom_by(self, factor: float, *, view_pos: QPointF | QPoint | None = None) -> None:
        """Zoom by ``factor``, keeping ``view_pos`` (default: center) anchored."""
        if not self.has_image:
            return
        if view_pos is None:
            view_pos = self._viewport_center()
        self._zoom_by(factor, QPointF(view_pos), self.ZOOM_ANIMATION_MS)

    def finish_animations(self) -> None:
        """Jump to the end of every running animation (tests, screenshots)."""
        if self._zoom_animation.state() == QAbstractAnimation.State.Running:
            self._zoom_animation.stop()
            self._apply_zoom_target()
            self._zoom_start = self._zoom
            self._zoom_target = self._zoom

        self._opacity_animation.stop()
        if self.has_image:
            self._pixmap_item.setOpacity(1.0)

        self._drop_animation.stop()
        self._drop_alpha = 1.0 if self._drop_active else 0.0
        self.viewport().update()

    def _viewport_center(self) -> QPointF:
        rect = self.viewport().rect()
        return QPointF(rect.width() / 2.0, rect.height() / 2.0)

    def _image_center(self) -> QPointF:
        return self._pixmap_item.boundingRect().center()

    @staticmethod
    def _same_point(a: QPointF, b: QPointF) -> bool:
        return abs(a.x() - b.x()) < 1e-6 and abs(a.y() - b.y()) < 1e-6

    def _zoom_by(self, factor: float, view_pos: QPointF, duration: int) -> None:
        base = self._zoom_target if self.is_zooming else self._zoom
        self._animate_zoom_to(
            self._clamp_zoom(base * factor),
            view_pos,
            duration,
            fit_mode=False,
        )

    def _animate_zoom_to(
        self,
        target: float,
        anchor: QPointF,
        duration: int,
        *,
        fit_mode: bool,
        anchor_image: QPointF | None = None,
    ) -> None:
        target = self._clamp_zoom(target)
        self._fit_mode = fit_mode
        if anchor_image is None:
            anchor_image = self.view_to_image(anchor)

        if fit_mode:
            target_center = self._clamped_center(self._image_center(), target)
            blend_center = True
        else:
            anchor_center = self._zoom_center_for(anchor, anchor_image, target)
            target_center = self._clamped_center(anchor_center, target)
            blend_center = not self._same_point(target_center, anchor_center)

        if abs(target - self._zoom) < 1e-9:
            self._zoom_animation.stop()
            self._zoom_start = target
            self._zoom_target = target
            self._zoom_anchor = anchor
            self._zoom_anchor_image = anchor_image
            self._zoom_start_center = self._center
            self._zoom_target_center = target_center
            self._zoom_blend_center = blend_center
            if fit_mode and not self._same_point(self._center, target_center):
                # Center at the current scale with a short slide.
                self._zoom_animation.setDuration(duration or self.ZOOM_ANIMATION_MS)
                self._zoom_animation.start()
            elif fit_mode:
                self._apply_camera(target, target_center)
            return

        self._zoom_animation.stop()
        self._zoom_start = self._zoom
        self._zoom_target = target
        self._zoom_anchor = anchor
        self._zoom_anchor_image = anchor_image
        self._zoom_start_center = self._center
        self._zoom_target_center = target_center
        self._zoom_blend_center = blend_center

        if duration <= 0:
            self._apply_zoom_target()
            return

        self._zoom_animation.setDuration(duration)
        self._zoom_animation.start()

    def _on_zoom_tick(self, value) -> None:
        start = self._zoom_start
        target = self._zoom_target
        if start <= 0.0 or target <= 0.0:
            return

        progress = max(0.0, min(1.0, float(value)))
        # Interpolate in log space so each animation frame feels equally fast.
        zoom = math.exp(math.log(start) + (math.log(target) - math.log(start)) * progress)
        if self._zoom_blend_center:
            center = (
                self._zoom_start_center
                + (self._zoom_target_center - self._zoom_start_center) * progress
            )
        else:
            # Keep the anchor exactly under the same viewport point. Edges are
            # not clamped mid-flight, which would make the image reverse
            # direction when it first becomes larger than the viewport.
            center = self._zoom_center_for(self._zoom_anchor, self._zoom_anchor_image, zoom)
        self._apply_camera(zoom, center, clamp=False)

    def _on_zoom_finished(self) -> None:
        self._apply_zoom_target()

    def _apply_zoom_target(self) -> None:
        self._apply_camera(self._zoom_target, self._zoom_target_center)
        self._zoom_start = self._zoom
        self._zoom_target = self._zoom
        self._zoom_start_center = self._center
        self._zoom_target_center = self._center
        self._zoom_blend_center = False

    def _zoom_center_for(self, anchor: QPointF, anchor_image: QPointF, zoom: float) -> QPointF:
        return anchor_image - (anchor - self._viewport_center()) / zoom

    def _apply_camera(self, factor: float, center: QPointF, *, clamp: bool = True) -> None:
        """Position the image with a floating-point transform.

        The image item is transformed instead of the view so scrollbars cannot
        quantise the animation to whole pixels.
        """
        if not self.has_image:
            return

        factor = self._clamp_zoom(factor)
        if clamp:
            center = self._clamped_center(center, factor)
        view_center = self._viewport_center()
        transform = QTransform(
            factor,
            0.0,
            0.0,
            factor,
            view_center.x() - center.x() * factor,
            view_center.y() - center.y() * factor,
        )
        self._pixmap_item.setTransform(transform)

        changed = abs(factor - self._zoom) >= 1e-9
        self._zoom = factor
        self._center = center
        if changed:
            self.zoomChanged.emit(factor * 100)

    def _clamped_center(self, center: QPointF, factor: float) -> QPointF:
        """Keep the image inside the familiar scrollable bounds."""
        if not self.has_image or factor <= 0.0:
            return QPointF()

        pixmap = self._pixmap_item.pixmap()
        viewport = self.viewport().rect()
        if viewport.width() <= 0 or viewport.height() <= 0:
            return center

        half_width = viewport.width() / (2.0 * factor)
        half_height = viewport.height() / (2.0 * factor)
        if pixmap.width() <= 2.0 * half_width:
            x = pixmap.width() / 2.0
        else:
            x = min(max(center.x(), half_width), pixmap.width() - half_width)

        if pixmap.height() <= 2.0 * half_height:
            y = pixmap.height() / 2.0
        else:
            y = min(max(center.y(), half_height), pixmap.height() - half_height)
        return QPointF(x, y)

    def _clamp_zoom(self, factor: float) -> float:
        return max(self.MIN_ZOOM, min(self.MAX_ZOOM, factor))

    def _fit_scale(self) -> float | None:
        if not self.has_image:
            return None

        pixmap = self._pixmap_item.pixmap()
        viewport_width = self.viewport().width()
        viewport_height = self.viewport().height()
        if viewport_width <= 1 or viewport_height <= 1:
            return None

        scale = min(
            (viewport_width - 2) / pixmap.width(),
            (viewport_height - 2) / pixmap.height(),
            1.0,
        )
        return max(scale, self.MIN_ZOOM)

    def _fit_now(self) -> None:
        scale = self._fit_scale()
        if scale is None:
            return

        self._zoom_animation.stop()
        self._fit_mode = True
        self._apply_camera(scale, self._image_center())
        self._zoom_start = self._zoom
        self._zoom_target = self._zoom
        self._zoom_start_center = self._center
        self._zoom_target_center = self._center
        self._zoom_blend_center = False

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.has_image:
            if self._fit_mode:
                # Resize must not fight the user with a new animation per event.
                self._fit_now()
            elif self._zoom > 0.0:
                # The camera is relative to the viewport center, so keep the
                # image centered around the same point while the window resizes.
                self._apply_camera(self._zoom, self._center)
        if not self.has_image and not self._drop_active:
            self._position_open_button()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self.has_image and not self._drop_active:
            self._position_open_button()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not self.has_image:
            event.accept()
            return

        angle_delta = event.angleDelta().y()
        pixel_delta = event.pixelDelta().y()
        if angle_delta:
            steps = angle_delta / 120.0
        elif pixel_delta:
            # Precision touchpads deliver many small deltas; this keeps the
            # zoom continuous instead of jumping by a full wheel notch.
            steps = pixel_delta / 50.0
        else:
            super().wheelEvent(event)
            return

        self._zoom_by(
            self.ZOOM_STEP**steps,
            QPointF(event.position()),
            self.WHEEL_ANIMATION_MS,
        )
        event.accept()

    # -- panning ---------------------------------------------------------
    def mousePressEvent(self, event) -> None:
        wants_pan = self.has_image and event.button() in (
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.MiddleButton,
        )
        if wants_pan:
            if self.is_zooming:
                # Continue from where the animation is instead of jumping to
                # its target when the user starts dragging.
                self._zoom_animation.stop()
                self._zoom_start = self._zoom
                self._zoom_target = self._zoom
            self._panning = True
            self._pan_origin = event.position()
            self._update_cursor()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
            delta = event.position() - self._pan_origin
            self._pan_origin = event.position()
            if self._zoom > 0.0:
                self._apply_camera(self._zoom, self._center - delta / self._zoom)
            event.accept()
            return

        super().mouseMoveEvent(event)
        self._emit_cursor_position(event.position().toPoint())

    def mouseReleaseEvent(self, event) -> None:
        if self._panning and event.button() in (
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.MiddleButton,
        ):
            self._panning = False
            self._update_cursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event) -> None:
        self.cursorPositionChanged.emit(None)
        super().leaveEvent(event)

    def _update_cursor(self) -> None:
        if self._panning:
            cursor = Qt.CursorShape.ClosedHandCursor
        elif self.has_image:
            cursor = Qt.CursorShape.OpenHandCursor
        else:
            cursor = Qt.CursorShape.ArrowCursor
        self.viewport().setCursor(cursor)

    def _emit_cursor_position(self, view_pos: QPoint) -> None:
        if not self.has_image:
            self.cursorPositionChanged.emit(None)
            return
        image_pos = self.view_to_image(QPointF(view_pos))
        if self._pixmap_item.boundingRect().contains(image_pos):
            self.cursorPositionChanged.emit(image_pos)
        else:
            self.cursorPositionChanged.emit(None)

    # -- drag and drop highlight -----------------------------------------
    def set_drop_active(self, active: bool) -> None:
        if active == self._drop_active:
            return
        self._drop_active = active
        self._update_open_button()
        self._drop_animation.stop()
        self._drop_animation.setStartValue(self._drop_alpha)
        self._drop_animation.setEndValue(1.0 if active else 0.0)
        self._drop_animation.setDuration(self.DROP_FADE_MS)
        self._drop_animation.start()

    def _update_open_button(self) -> None:
        visible = not self.has_image and not self._drop_active
        self._open_button.setVisible(visible)
        if visible:
            self._position_open_button()

    def _position_open_button(self) -> None:
        hint = self._open_button.sizeHint()
        self._open_button.resize(hint)
        x = (self.viewport().width() - hint.width()) // 2
        y = self.viewport().height() // 2 + 48
        self._open_button.move(max(0, x), max(0, y))

    def _on_drop_tick(self, value) -> None:
        self._drop_alpha = max(0.0, min(1.0, float(value)))
        self.viewport().update()

    def _on_opacity_tick(self, value) -> None:
        self._pixmap_item.setOpacity(max(0.0, min(1.0, float(value))))

    # -- painting --------------------------------------------------------
    @staticmethod
    def _make_grid_brush() -> QBrush:
        tile = QPixmap(48, 48)
        tile.setDevicePixelRatio(2)
        tile.fill(Qt.GlobalColor.transparent)

        painter = QPainter(tile)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.scale(2, 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 12))
        painter.drawEllipse(QPointF(12.0, 12.0), 1.0, 1.0)
        painter.end()
        return QBrush(tile)

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        painter.resetTransform()
        viewport_rect = self.viewport().rect()

        gradient = QLinearGradient(0.0, 0.0, 0.0, float(viewport_rect.height()))
        gradient.setColorAt(0.0, QColor("#13161c"))
        gradient.setColorAt(1.0, QColor("#0b0d11"))
        painter.fillRect(viewport_rect, gradient)
        painter.fillRect(viewport_rect, self._grid_brush)
        painter.restore()

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        super().drawForeground(painter, rect)

        if self.has_image:
            pen = QPen(QColor(255, 255, 255, 26))
            pen.setWidthF(0.0)
            pen.setCosmetic(True)
            painter.save()
            painter.setTransform(self._pixmap_item.sceneTransform(), True)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self._pixmap_item.boundingRect())
            painter.restore()
        else:
            self._draw_placeholder(painter)

        if self._drop_alpha > 0.001:
            self._draw_drop_overlay(painter)

    def _draw_placeholder(self, painter: QPainter) -> None:
        painter.save()
        painter.resetTransform()
        viewport_rect = self.viewport().rect()
        cx = viewport_rect.center().x() + 0.5
        cy = viewport_rect.center().y() + 0.5

        icon_rect = QRectF(cx - 33.0, cy - 126.0, 66.0, 66.0)
        painter.setPen(QPen(QColor(91, 140, 255, 130), 1.6))
        painter.setBrush(QColor(91, 140, 255, 16))
        painter.drawRoundedRect(icon_rect, 17.0, 17.0)

        painter.setPen(QPen(QColor(150, 178, 255, 220), 1.7))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx - 12.0, cy - 101.0), 4.0, 4.0)
        mountains = QPainterPath()
        mountains.moveTo(cx - 21.0, cy - 69.0)
        mountains.lineTo(cx - 5.0, cy - 89.0)
        mountains.lineTo(cx + 6.0, cy - 78.0)
        mountains.lineTo(cx + 13.0, cy - 86.0)
        mountains.lineTo(cx + 21.0, cy - 72.0)
        painter.drawPath(mountains)

        title_font = QFont(self.font())
        title_font.setPointSizeF(15.0)
        title_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(title_font)
        painter.setPen(QColor("#e3e8f2"))
        painter.drawText(
            QRectF(float(viewport_rect.left()), cy - 38.0, float(viewport_rect.width()), 34.0),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            "拖入图片，开始编辑",
        )

        hint_font = QFont(self.font())
        hint_font.setPointSizeF(9.5)
        painter.setFont(hint_font)
        painter.setPen(QColor("#7f8899"))
        painter.drawText(
            QRectF(float(viewport_rect.left()), cy + 2.0, float(viewport_rect.width()), 24.0),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            "Ctrl+O 打开文件    ·    滚轮缩放    ·    左键拖动平移",
        )
        painter.restore()

    def _draw_drop_overlay(self, painter: QPainter) -> None:
        painter.save()
        painter.resetTransform()
        viewport_rect = self.viewport().rect()
        alpha = max(0.0, min(1.0, self._drop_alpha))

        painter.fillRect(viewport_rect, QColor(9, 11, 15, int(150 * alpha)))
        border = viewport_rect.adjusted(16, 16, -16, -16)
        pen = QPen(QColor(91, 140, 255, int(225 * alpha)), 2.0, Qt.PenStyle.DashLine)
        pen.setDashPattern([6.0, 4.0])
        painter.setPen(pen)
        painter.setBrush(QColor(91, 140, 255, int(18 * alpha)))
        painter.drawRoundedRect(QRectF(border), 18.0, 18.0)

        title_font = QFont(self.font())
        title_font.setPointSizeF(15.0)
        title_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(title_font)
        painter.setPen(QColor(225, 234, 255, int(255 * alpha)))
        painter.drawText(
            viewport_rect.adjusted(0, -18, 0, -18),
            Qt.AlignmentFlag.AlignCenter,
            "松开以打开图片",
        )

        hint_font = QFont(self.font())
        hint_font.setPointSizeF(9.5)
        painter.setFont(hint_font)
        painter.setPen(QColor(160, 180, 220, int(235 * alpha)))
        painter.drawText(
            viewport_rect.adjusted(0, 44, 0, 44),
            Qt.AlignmentFlag.AlignCenter,
            "将载入所拖入的图片",
        )
        painter.restore()
