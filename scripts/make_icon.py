"""Generate app/resources/icon.png and a multi-size icon.ico."""

from __future__ import annotations

import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "app" / "resources"
SIZES = (16, 32, 48, 64, 128, 256)


def render_icon(size: int) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    margin = size * 0.06
    side = size - margin * 2
    radius = side * 0.24

    background = QPainterPath()
    background.addRoundedRect(QRectF(margin, margin, side, side), radius, radius)
    gradient = QLinearGradient(margin, margin, margin + side, margin + side)
    gradient.setColorAt(0.0, QColor("#5b8cff"))
    gradient.setColorAt(1.0, QColor("#6a5cff"))
    painter.fillPath(background, gradient)

    frame_width = side * 0.58
    frame_height = side * 0.48
    frame_x = margin + (side - frame_width) / 2
    frame_y = margin + (side - frame_height) / 2
    frame = QRectF(frame_x, frame_y, frame_width, frame_height)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 255, 255, 235))
    painter.drawRoundedRect(frame, side * 0.05, side * 0.05)

    painter.setBrush(QColor("#ffd166"))
    sun_radius = side * 0.07
    painter.drawEllipse(
        QPointF(frame_x + frame_width * 0.28, frame_y + frame_height * 0.32),
        sun_radius,
        sun_radius,
    )

    painter.save()
    clip = QPainterPath()
    clip.addRoundedRect(frame, side * 0.05, side * 0.05)
    painter.setClipPath(clip)

    painter.setBrush(QColor("#2447b8"))
    left_mountain = QPainterPath()
    left_mountain.moveTo(frame_x - side * 0.02, frame_y + frame_height)
    left_mountain.lineTo(frame_x + frame_width * 0.32, frame_y + frame_height * 0.42)
    left_mountain.lineTo(frame_x + frame_width * 0.58, frame_y + frame_height)
    left_mountain.closeSubpath()
    painter.drawPath(left_mountain)

    painter.setBrush(QColor("#3b82f6"))
    right_mountain = QPainterPath()
    right_mountain.moveTo(frame_x + frame_width * 0.35, frame_y + frame_height)
    right_mountain.lineTo(frame_x + frame_width * 0.68, frame_y + frame_height * 0.30)
    right_mountain.lineTo(frame_x + frame_width * 1.02, frame_y + frame_height)
    right_mountain.closeSubpath()
    painter.drawPath(right_mountain)
    painter.restore()

    painter.end()
    return image


def png_bytes(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise RuntimeError("Failed to encode PNG")
    buffer.close()
    return bytes(data)


def write_ico(path: Path, images: list[QImage]) -> None:
    payloads = [png_bytes(image) for image in images]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)

    entries: list[bytes] = []
    for image, payload in zip(images, payloads, strict=True):
        width = 0 if image.width() >= 256 else image.width()
        height = 0 if image.height() >= 256 else image.height()
        entries.append(
            struct.pack(
                "<BBBBHHII",
                width,
                height,
                0,
                0,
                1,
                32,
                len(payload),
                offset,
            )
        )
        offset += len(payload)

    path.write_bytes(header + b"".join(entries) + b"".join(payloads))


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    master = render_icon(256)
    master_path = OUTPUT_DIR / "icon.png"
    if not master.save(str(master_path), "PNG"):
        raise SystemExit("Failed to write icon.png")

    write_ico(OUTPUT_DIR / "icon.ico", [render_icon(size) for size in SIZES])
    print(f"Wrote {master_path}")
    print(f"Wrote {OUTPUT_DIR / 'icon.ico'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
