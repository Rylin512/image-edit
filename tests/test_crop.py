from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.ui.canvas import CanvasView
from app.ui.crop import CropOverlay


def make_image(width: int = 1600, height: int = 1200) -> QImage:
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor("#2b8a3e"))
    return image


def make_canvas(qapp: QApplication) -> CanvasView:
    canvas = CanvasView()
    canvas.resize(600, 400)
    canvas.set_image(make_image(), reset_view=True)
    canvas.show()
    qapp.processEvents()
    return canvas


def crop_overlay(canvas: CanvasView) -> CropOverlay:
    overlay = canvas.findChild(CropOverlay)
    assert overlay is not None
    return overlay


def test_free_crop_starts_with_the_whole_image(qapp: QApplication) -> None:
    canvas = make_canvas(qapp)

    canvas.begin_crop()

    assert canvas.is_cropping
    assert crop_overlay(canvas).isVisible()
    assert canvas.crop_rect() == QRect(0, 0, 1600, 1200)
    canvas.cancel_crop()
    assert not canvas.is_cropping
    canvas.close()
    canvas.deleteLater()


def test_ratio_crop_starts_centered_at_the_requested_aspect(qapp: QApplication) -> None:
    canvas = make_canvas(qapp)

    canvas.begin_crop(16 / 9)

    rect = canvas.crop_rect()
    assert rect.width() == 1600
    assert rect.height() == 900
    assert rect.top() == 150
    assert rect.width() / rect.height() == pytest.approx(16 / 9, abs=1e-3)
    canvas.close()
    canvas.deleteLater()


def test_invalid_aspect_falls_back_to_free_cropping(qapp: QApplication) -> None:
    canvas = make_canvas(qapp)
    canvas.begin_crop(0.0)
    qapp.processEvents()
    overlay = crop_overlay(canvas)
    handle = canvas.image_to_view(canvas.image_rect().bottomRight()).toPoint()
    target = handle - QPoint(70, 55)

    QTest.mousePress(overlay, Qt.MouseButton.LeftButton, pos=handle)
    QTest.mouseMove(overlay, target, delay=10)
    QTest.mouseRelease(overlay, Qt.MouseButton.LeftButton, pos=target)

    rect = canvas.crop_rect()
    assert 0 < rect.width() < 1600
    assert 0 < rect.height() < 1200
    canvas.close()
    canvas.deleteLater()


def test_dragging_a_corner_resizes_the_selection(qapp: QApplication) -> None:
    canvas = make_canvas(qapp)
    canvas.begin_crop()
    qapp.processEvents()
    overlay = crop_overlay(canvas)
    handle = canvas.image_to_view(canvas.image_rect().bottomRight()).toPoint()
    target = handle - QPoint(70, 55)

    QTest.mousePress(overlay, Qt.MouseButton.LeftButton, pos=handle)
    QTest.mouseMove(overlay, target, delay=10)
    QTest.mouseRelease(overlay, Qt.MouseButton.LeftButton, pos=target)

    rect = canvas.crop_rect()
    assert 0 < rect.width() < 1600
    assert 0 < rect.height() < 1200
    assert canvas.image_rect().contains(QRectF(rect))
    canvas.close()
    canvas.deleteLater()


def test_dragging_a_ratio_corner_keeps_the_aspect_lock(qapp: QApplication) -> None:
    canvas = make_canvas(qapp)
    canvas.begin_crop(1.0)
    qapp.processEvents()
    overlay = crop_overlay(canvas)
    handle = canvas.image_to_view(QPointF(1400, 1200)).toPoint()
    target = handle - QPoint(45, 60)

    QTest.mousePress(overlay, Qt.MouseButton.LeftButton, pos=handle)
    QTest.mouseMove(overlay, target, delay=10)
    QTest.mouseRelease(overlay, Qt.MouseButton.LeftButton, pos=target)

    rect = canvas.crop_rect()
    assert abs(rect.width() - rect.height()) <= 1
    canvas.close()
    canvas.deleteLater()


def test_accept_crop_emits_the_selection(qapp: QApplication) -> None:
    canvas = make_canvas(qapp)
    accepted: list[QRect] = []
    canvas.cropAccepted.connect(accepted.append)
    canvas.begin_crop()

    canvas.accept_crop()

    assert accepted == [QRect(0, 0, 1600, 1200)]
    assert not canvas.is_cropping
    canvas.close()
    canvas.deleteLater()


def test_cancel_emits_once_and_hides_the_overlay(qapp: QApplication) -> None:
    canvas = make_canvas(qapp)
    cancelled: list[bool] = []
    canvas.cropCancelled.connect(lambda: cancelled.append(True))
    canvas.begin_crop()

    canvas.cancel_crop()
    canvas.cancel_crop()

    assert cancelled == [True]
    assert not canvas.is_cropping
    assert not crop_overlay(canvas).isVisible()
    canvas.close()
    canvas.deleteLater()


def test_wheel_does_not_zoom_while_cropping(qapp: QApplication) -> None:
    canvas = make_canvas(qapp)
    canvas.begin_crop()
    before = canvas.zoom_factor

    pos = QPointF(canvas.viewport().rect().center())
    event = QWheelEvent(
        pos,
        pos,
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(canvas.viewport(), event)

    assert canvas.zoom_factor == pytest.approx(before)
    canvas.close()
    canvas.deleteLater()


def test_replacing_the_image_stops_cropping(qapp: QApplication) -> None:
    canvas = make_canvas(qapp)
    canvas.begin_crop()

    canvas.set_image(make_image(200, 100))

    assert not canvas.is_cropping
    canvas.close()
    canvas.deleteLater()
