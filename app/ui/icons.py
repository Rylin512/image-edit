"""Line icons drawn with QPainter.

Keeping icons in code avoids shipping extra assets and lets the whole UI use
one stroke color. Each icon is rendered at 1x, 2x and 3x so it stays crisp on
high-DPI displays.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap

ICON_COLOR = "#c9d2e2"
DISABLED_COLOR = "#5c6474"
_SIZE = 24


def _pen(color: str, width: float = 1.7) -> QPen:
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _draw(name: str, painter: QPainter, color: str) -> None:
    painter.setPen(_pen(color))
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if name == "open":
        path = QPainterPath()
        path.moveTo(3.2, 7.0)
        path.lineTo(8.8, 7.0)
        path.lineTo(10.8, 9.0)
        path.lineTo(20.8, 9.0)
        path.lineTo(20.8, 18.8)
        path.lineTo(3.2, 18.8)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(3.2, 11.2), QPointF(20.8, 11.2))

    elif name == "save":
        painter.drawRoundedRect(QRectF(4.0, 4.0, 16.0, 16.0), 2.4, 2.4)
        notch = QPainterPath()
        notch.moveTo(8.4, 4.2)
        notch.lineTo(8.4, 9.6)
        notch.lineTo(15.6, 9.6)
        notch.lineTo(15.6, 4.2)
        painter.drawPath(notch)
        painter.drawRoundedRect(QRectF(7.6, 13.6, 8.8, 6.2), 1.1, 1.1)

    elif name == "save_as":
        painter.drawRoundedRect(QRectF(3.0, 4.4, 13.6, 14.2), 2.2, 2.2)
        notch = QPainterPath()
        notch.moveTo(6.8, 4.6)
        notch.lineTo(6.8, 9.0)
        notch.lineTo(12.8, 9.0)
        notch.lineTo(12.8, 4.6)
        painter.drawPath(notch)
        painter.drawLine(QPointF(15.0, 16.2), QPointF(20.6, 16.2))
        painter.drawLine(QPointF(17.8, 13.4), QPointF(20.6, 16.2))
        painter.drawLine(QPointF(17.8, 19.0), QPointF(20.6, 16.2))

    elif name in {"undo", "redo"}:
        if name == "redo":
            painter.save()
            painter.translate(_SIZE, 0)
            painter.scale(-1, 1)

        # A left-pointing arrow whose tail loops down and back, like the
        # common "return" undo glyph. The arrowhead and tail share one vertex
        # so the stroke reads as a single continuous path.
        tip = QPointF(4.0, 8.2)
        painter.drawLine(tip, QPointF(9.0, 3.2))
        painter.drawLine(tip, QPointF(9.0, 13.2))

        tail = QPainterPath(tip)
        tail.lineTo(14.5, 8.2)
        tail.cubicTo(17.5, 8.2, 20.0, 10.7, 20.0, 13.5)
        tail.lineTo(20.0, 13.8)
        tail.cubicTo(20.0, 16.7, 17.5, 19.2, 14.5, 19.2)
        tail.lineTo(10.0, 19.2)
        painter.drawPath(tail)

        if name == "redo":
            painter.restore()

    elif name in {"zoom_in", "zoom_out"}:
        painter.drawEllipse(QRectF(4.2, 4.2, 11.6, 11.6))
        painter.drawLine(QPointF(16.2, 16.2), QPointF(20.2, 20.2))
        painter.drawLine(QPointF(7.2, 10.0), QPointF(12.8, 10.0))
        if name == "zoom_in":
            painter.drawLine(QPointF(10.0, 7.2), QPointF(10.0, 12.8))

    elif name in {"rotate_left", "rotate_right"}:
        if name == "rotate_left":
            painter.save()
            painter.translate(_SIZE, 0)
            painter.scale(-1, 1)

        # A broad 240-degree sweep leaves an obvious opening on the right and
        # ends in a solid arrow at the top. Both the gap and the filled head
        # make the turn direction readable even at toolbar size; a 270-degree
        # arc looked too much like a refresh loop.
        circle = QRectF(5.5, 5.5, 13.0, 13.0)
        path = QPainterPath()
        path.arcMoveTo(circle, 330.0)
        path.arcTo(circle, 330.0, -240.0)
        painter.drawPath(path)

        head = QPainterPath(QPointF(14.2, 5.5))
        head.lineTo(9.0, 2.6)
        head.lineTo(9.0, 8.4)
        head.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        painter.drawPath(head)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if name == "rotate_left":
            painter.restore()

    elif name == "chevron_down":
        path = QPainterPath()
        path.moveTo(6.6, 9.4)
        path.lineTo(12.0, 14.8)
        path.lineTo(17.4, 9.4)
        painter.drawPath(path)

    elif name in {"flip_horizontal", "flip_vertical"}:
        painter.save()
        if name == "flip_vertical":
            painter.translate(12.0, 12.0)
            painter.rotate(90.0)
            painter.translate(-12.0, -12.0)

        axis_pen = _pen(color, 1.3)
        axis_pen.setDashPattern([2.4, 2.6])
        painter.setPen(axis_pen)
        painter.drawLine(QPointF(12.0, 3.2), QPointF(12.0, 20.8))

        painter.setPen(_pen(color, 1.5))
        left = QPainterPath()
        left.moveTo(3.6, 12.0)
        left.lineTo(9.2, 6.4)
        left.lineTo(9.2, 17.6)
        left.closeSubpath()
        painter.drawPath(left)

        right = QPainterPath()
        right.moveTo(20.4, 12.0)
        right.lineTo(14.8, 6.4)
        right.lineTo(14.8, 17.6)
        right.closeSubpath()
        painter.drawPath(right)
        painter.restore()

    elif name == "crop":
        top_left = QPainterPath()
        top_left.moveTo(7.0, 3.8)
        top_left.lineTo(7.0, 17.0)
        top_left.lineTo(20.2, 17.0)
        painter.drawPath(top_left)

        bottom_right = QPainterPath()
        bottom_right.moveTo(3.8, 7.0)
        bottom_right.lineTo(17.0, 7.0)
        bottom_right.lineTo(17.0, 20.2)
        painter.drawPath(bottom_right)

    elif name == "fit":
        for points in (
            ((3.4, 9.0), (3.4, 3.4), (9.0, 3.4)),
            ((15.0, 3.4), (20.6, 3.4), (20.6, 9.0)),
            ((20.6, 15.0), (20.6, 20.6), (15.0, 20.6)),
            ((9.0, 20.6), (3.4, 20.6), (3.4, 15.0)),
        ):
            path = QPainterPath()
            path.moveTo(*points[0])
            path.lineTo(*points[1])
            path.lineTo(*points[2])
            painter.drawPath(path)

    elif name == "actual":
        font = QFont()
        font.setFamilies(["Segoe UI Variable Text", "Segoe UI", "Microsoft YaHei UI"])
        font.setPixelSize(9)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(color))
        painter.drawText(
            QRectF(0.0, 0.0, float(_SIZE), float(_SIZE)),
            Qt.AlignmentFlag.AlignCenter,
            "1:1",
        )

    else:
        raise ValueError(f"Unknown icon: {name}")


def _render(name: str, color: str, scale: int) -> QPixmap:
    # Each entry is a separate resolution; letting Qt choose and scale it is
    # what keeps toolbar icons complete at fractional display scaling.
    physical = _SIZE * scale
    pixmap = QPixmap(physical, physical)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.scale(scale, scale)
    _draw(name, painter, color)
    painter.end()
    return pixmap


def make_icon(name: str, color: str = ICON_COLOR) -> QIcon:
    """Return a multi-resolution icon for ``name``."""
    icon = QIcon()
    for scale in (1, 2, 3):
        icon.addPixmap(_render(name, color, scale), QIcon.Mode.Normal)
        icon.addPixmap(_render(name, DISABLED_COLOR, scale), QIcon.Mode.Disabled)
    return icon
