from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QImage, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from app.ui.canvas import CanvasView


def make_image(width: int = 1200, height: int = 800) -> QImage:
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor("#2b8a3e"))
    return image


def send_wheel(canvas: CanvasView, delta: int, pos: QPointF | None = None) -> None:
    if pos is None:
        pos = QPointF(canvas.viewport().rect().center())
    event = QWheelEvent(
        pos,
        pos,
        QPoint(0, 0),
        QPoint(0, delta),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(canvas.viewport(), event)


def settle(canvas: CanvasView) -> None:
    """Skip the easing animation so assertions see the final zoom."""
    canvas.finish_animations()


def image_origin(canvas: CanvasView) -> QPoint:
    """Viewport position of the image's top-left corner."""
    return canvas.image_to_view(QPointF(0, 0)).toPoint()


def image_center_in_view(canvas: CanvasView) -> QPoint:
    """Viewport position of the image's center."""
    return canvas.image_to_view(canvas.image_rect().center()).toPoint()


def test_empty_canvas(qapp: QApplication) -> None:
    canvas = CanvasView()
    assert not canvas.has_image
    assert canvas.zoom_factor == 0.0


def test_empty_canvas_offers_a_centered_open_button(qapp: QApplication) -> None:
    canvas = CanvasView()
    canvas.resize(600, 400)
    canvas.show()
    qapp.processEvents()

    button = canvas.findChild(QPushButton, "empty_open_button")
    assert button is not None
    assert button.isVisible()
    assert abs(button.geometry().center().x() - canvas.viewport().width() // 2) <= 2

    triggered: list[bool] = []
    canvas.openRequested.connect(lambda: triggered.append(True))
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    assert triggered

    canvas.set_image(make_image())
    qapp.processEvents()
    assert not button.isVisible()

    canvas.close()
    canvas.deleteLater()


def test_large_image_fits_window(qapp: QApplication) -> None:
    canvas = CanvasView()
    canvas.resize(400, 300)
    canvas.set_image(make_image(), reset_view=True)

    assert canvas.has_image
    assert 0 < canvas.zoom_factor < 1.0
    canvas.deleteLater()


def test_small_image_is_not_upscaled(qapp: QApplication) -> None:
    canvas = CanvasView()
    canvas.resize(800, 600)
    canvas.set_image(make_image(80, 60), reset_view=True)

    assert canvas.zoom_factor == pytest.approx(1.0)
    canvas.deleteLater()


def test_zoom_is_clamped_and_actual_size_works(qapp: QApplication) -> None:
    canvas = CanvasView()
    canvas.resize(400, 300)
    canvas.set_image(make_image(), reset_view=True)

    canvas.zoom_by(10_000)
    settle(canvas)
    assert canvas.zoom_factor == pytest.approx(CanvasView.MAX_ZOOM)

    canvas.zoom_by(1e-6)
    settle(canvas)
    assert canvas.zoom_factor == pytest.approx(CanvasView.MIN_ZOOM)

    canvas.actual_size()
    settle(canvas)
    assert canvas.zoom_factor == pytest.approx(1.0)
    canvas.deleteLater()


def test_wheel_zooms_without_modifier(qapp: QApplication) -> None:
    canvas = CanvasView()
    canvas.resize(400, 300)
    canvas.set_image(make_image(), reset_view=True)
    before = canvas.zoom_factor

    send_wheel(canvas, 120)
    settle(canvas)
    assert canvas.zoom_factor == pytest.approx(before * CanvasView.ZOOM_STEP)

    send_wheel(canvas, -120)
    settle(canvas)
    assert canvas.zoom_factor == pytest.approx(before)
    canvas.deleteLater()


def test_wheel_zoom_keeps_point_under_cursor(qapp: QApplication) -> None:
    canvas = CanvasView()
    canvas.resize(500, 400)
    canvas.set_image(make_image(1600, 1200), reset_view=True)
    cursor = QPoint(380, 290)
    before = canvas.mapToScene(cursor)

    send_wheel(canvas, 120, QPointF(cursor))
    settle(canvas)

    after = canvas.mapToScene(cursor)
    # Sub-pixel accuracy is enough; QGraphicsView rounds scroll positions.
    assert after.x() == pytest.approx(before.x(), abs=3.0)
    assert after.y() == pytest.approx(before.y(), abs=3.0)
    canvas.deleteLater()


def test_left_drag_pans_image(qapp: QApplication) -> None:
    canvas = CanvasView()
    canvas.resize(400, 300)
    canvas.set_image(make_image(2000, 1500), reset_view=True)
    canvas.show()
    qapp.processEvents()
    canvas.actual_size()
    settle(canvas)
    qapp.processEvents()

    origin_before = image_origin(canvas)

    QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(200, 150))
    QTest.mouseMove(canvas.viewport(), QPoint(150, 100), delay=10)
    QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(150, 100))

    origin_after = image_origin(canvas)
    assert origin_after.x() == origin_before.x() - 50
    assert origin_after.y() == origin_before.y() - 50
    canvas.close()
    canvas.deleteLater()


def test_zoom_animation_keeps_the_anchor_still(qapp: QApplication) -> None:
    canvas = CanvasView()
    canvas.resize(500, 400)
    canvas.set_image(make_image(1600, 1200), reset_view=True)
    cursor = QPointF(380, 290)
    anchor_before = canvas.view_to_image(cursor)
    before = canvas.zoom_factor

    canvas.zoom_by(1.6, view_pos=cursor)
    assert canvas.is_zooming
    for fraction in (0.15, 0.4, 0.7, 0.95):
        canvas.advance_zoom_animation(fraction)
        anchor_now = canvas.view_to_image(cursor)
        assert anchor_now.x() == pytest.approx(anchor_before.x(), abs=0.25)
        assert anchor_now.y() == pytest.approx(anchor_before.y(), abs=0.25)

    settle(canvas)
    assert canvas.zoom_factor == pytest.approx(before * 1.6)
    canvas.deleteLater()


def test_fit_slides_a_panned_image_back_to_the_center(qapp: QApplication) -> None:
    canvas = CanvasView()
    canvas.resize(500, 400)
    canvas.set_image(make_image(1600, 1200), reset_view=True)
    canvas.show()
    qapp.processEvents()
    canvas.actual_size()
    settle(canvas)
    qapp.processEvents()

    QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(250, 200))
    QTest.mouseMove(canvas.viewport(), QPoint(100, 100), delay=10)
    QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(100, 100))
    panned = image_center_in_view(canvas)
    assert panned != canvas.viewport().rect().center()

    canvas.fit_to_window()
    canvas.advance_zoom_animation(0.01)
    early = image_center_in_view(canvas)
    # The image slides toward the center instead of jumping there on frame 1.
    assert abs(early.x() - panned.x()) < 20
    assert abs(early.y() - panned.y()) < 20

    settle(canvas)
    fitted = image_center_in_view(canvas)
    assert fitted.x() == pytest.approx(canvas.viewport().width() // 2, abs=1)
    assert fitted.y() == pytest.approx(canvas.viewport().height() // 2, abs=1)
    canvas.close()
    canvas.deleteLater()


def test_zoom_uses_a_finishing_animation(qapp: QApplication) -> None:
    canvas = CanvasView()
    canvas.resize(400, 300)
    canvas.set_image(make_image(), reset_view=True)

    canvas.actual_size()
    assert canvas.is_zooming
    settle(canvas)

    assert not canvas.is_zooming
    assert canvas.zoom_factor == pytest.approx(1.0)
    canvas.deleteLater()


def test_clear_image(qapp: QApplication) -> None:
    canvas = CanvasView()
    canvas.set_image(make_image(20, 20))
    assert canvas.has_image

    canvas.clear_image()
    assert not canvas.has_image
    assert canvas.zoom_factor == 0.0
    canvas.deleteLater()
