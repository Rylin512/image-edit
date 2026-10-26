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

        head = QPainterPath()
        head.moveTo(9.0, 6.6)
        head.lineTo(4.6, 11.0)
        head.lineTo(9.0, 15.4)
        painter.drawPath(head)

        curve = QPainterPath()
        curve.moveTo(4.8, 11.0)
        curve.cubicTo(8.0, 16.8, 16.4, 16.8, 19.2, 10.6)
        painter.drawPath(curve)

        if name == "redo":
            painter.restore()

    elif name in {"zoom_in", "zoom_out"}:
        painter.drawEllipse(QRectF(4.2, 4.2, 11.6, 11.6))
        painter.drawLine(QPointF(16.2, 16.2), QPointF(20.2, 20.2))
        painter.drawLine(QPointF(7.2, 10.0), QPointF(12.8, 10.0))
        if name == "zoom_in":
            painter.drawLine(QPointF(10.0, 7.2), QPointF(10.0, 12.8))

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
