from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow

# Keep Qt headless on CI and on machines without a display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance() or QApplication([])
    app.setOrganizationName("Rylin512")
    app.setApplicationName("ImageEditTests")
    return app


@pytest.fixture()
def sample_image() -> QImage:
    image = QImage(48, 32, QImage.Format.Format_RGB32)
    image.fill(QColor("#e03131"))
    return image


@pytest.fixture()
def sample_image_path(tmp_path: Path, sample_image: QImage) -> Path:
    path = tmp_path / "sample.png"
    assert sample_image.save(str(path))
    return path


@pytest.fixture()
def settings(tmp_path: Path) -> QSettings:
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


@pytest.fixture()
def window(qapp: QApplication, settings: QSettings) -> Iterator[MainWindow]:
    win = MainWindow(settings=settings)
    yield win
    win.document.set_modified(False)
    win.close()
