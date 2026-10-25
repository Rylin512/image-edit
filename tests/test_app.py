from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from app.main import MainWindow, _suffix_from_filter, load_image, save_image

IMAGE_SIZE = 16


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def sample_image(tmp_path: Path) -> Path:
    image = QImage(IMAGE_SIZE, IMAGE_SIZE, QImage.Format.Format_RGB32)
    image.fill(QColor("red"))
    path = tmp_path / "sample.png"
    assert image.save(str(path))
    return path


def test_load_image(sample_image: Path) -> None:
    image = load_image(sample_image)
    assert not image.isNull()
    assert image.width() == IMAGE_SIZE
    assert image.height() == IMAGE_SIZE


def test_load_missing_image_returns_null(tmp_path: Path) -> None:
    assert load_image(tmp_path / "missing.png").isNull()


def test_save_image_roundtrip(sample_image: Path, tmp_path: Path) -> None:
    image = load_image(sample_image)
    target = tmp_path / "copy.png"
    assert save_image(image, target)
    assert not load_image(target).isNull()


def test_save_image_rejects_null_image(tmp_path: Path) -> None:
    assert not save_image(QImage(), tmp_path / "empty.png")


def test_suffix_from_filter() -> None:
    assert _suffix_from_filter("PNG 图片 (*.png)") == ".png"
    assert _suffix_from_filter("JPEG 图片 (*.jpg *.jpeg)") == ".jpg"
    assert _suffix_from_filter("未知过滤器") == ".png"


def test_window_starts_empty(qapp: QApplication) -> None:
    window = MainWindow()
    try:
        assert window.image.isNull()
        assert window.current_path is None
        assert window.windowTitle() == "Image Edit"
    finally:
        window.close()


def test_window_loads_image(qapp: QApplication, sample_image: Path) -> None:
    window = MainWindow()
    try:
        window.show()
        assert window.load_path(sample_image)
        assert window.image.width() == IMAGE_SIZE
        assert window.current_path == sample_image
        assert window.windowTitle().startswith(sample_image.name)
    finally:
        window.close()
