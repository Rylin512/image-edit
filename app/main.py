"""Entry point and main window for the image-edit desktop application."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QImage, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
)

OPEN_FILTER = "图片文件 (*.png *.jpg *.jpeg *.bmp *.webp *.gif);;所有文件 (*)"
EXPORT_FILTER = "PNG 图片 (*.png);;JPEG 图片 (*.jpg *.jpeg);;WebP 图片 (*.webp)"


def load_image(path: str | Path) -> QImage:
    """Return the image stored at path, or a null QImage if it cannot be read."""
    image = QImage()
    if not image.load(str(path)):
        return QImage()
    return image


def save_image(image: QImage, path: str | Path) -> bool:
    """Write image to path, returning False for an empty image or failed save."""
    return not image.isNull() and image.save(str(path))


def _suffix_from_filter(selected_filter: str) -> str:
    match = re.search(r"\*(\.[0-9A-Za-z]+)", selected_filter)
    return match.group(1) if match else ".png"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._image = QImage()
        self._current_path: Path | None = None

        self.setWindowTitle("Image Edit")
        self.resize(960, 640)

        self._canvas = QLabel("打开一张图片开始编辑")
        self._canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self._canvas.setMinimumSize(1, 1)

        scroll = QScrollArea()
        scroll.setWidget(self._canvas)
        scroll.setWidgetResizable(True)
        self.setCentralWidget(scroll)

        self._build_actions()
        self.statusBar().showMessage("就绪")

    @property
    def image(self) -> QImage:
        return self._image

    @property
    def current_path(self) -> Path | None:
        return self._current_path

    def _build_actions(self) -> None:
        open_action = QAction("打开(&O)", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_image)

        export_action = QAction("导出(&E)", self)
        export_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        export_action.triggered.connect(self.export_image)

        quit_action = QAction("退出(&Q)", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)

        file_menu = self.menuBar().addMenu("文件(&F)")
        file_menu.addAction(open_action)
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        file_menu.addAction(quit_action)

        toolbar = self.addToolBar("工具栏")
        toolbar.addAction(open_action)
        toolbar.addAction(export_action)

    def open_image(self) -> None:
        start_dir = self._current_path.parent if self._current_path else Path.home()
        path, _ = QFileDialog.getOpenFileName(self, "打开图片", str(start_dir), OPEN_FILTER)
        if path:
            self.load_path(path)

    def load_path(self, path: str | Path) -> bool:
        """Load path into the canvas; report failure to the user and return False."""
        image = load_image(path)
        if image.isNull():
            QMessageBox.warning(self, "打开失败", f"无法打开图片：\n{path}")
            return False

        self._current_path = Path(path)
        self._image = image
        self._canvas.setText("")
        self._update_pixmap()
        self.statusBar().showMessage(f"已打开 {self._current_path.name}")
        self.setWindowTitle(f"{self._current_path.name} - Image Edit")
        return True

    def export_image(self) -> None:
        if self._image.isNull():
            QMessageBox.information(self, "没有图片", "请先打开一张图片。")
            return

        stem = self._current_path.stem if self._current_path else "edited"
        start_dir = self._current_path.parent if self._current_path else Path.home()
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出图片",
            str(start_dir / f"{stem}-edited.png"),
            EXPORT_FILTER,
        )
        if not path:
            return

        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(_suffix_from_filter(selected_filter))

        if save_image(self._image, target):
            self.statusBar().showMessage(f"已导出 {target.name}")
        else:
            QMessageBox.warning(self, "导出失败", f"无法写入文件：\n{target}")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_pixmap()

    def _update_pixmap(self) -> None:
        if self._image.isNull() or self._canvas.width() <= 0 or self._canvas.height() <= 0:
            return
        pixmap = QPixmap.fromImage(self._image)
        self._canvas.setPixmap(
            pixmap.scaled(
                self._canvas.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


def main(argv: list[str] | None = None) -> int:
    app = QApplication(argv if argv is not None else sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
