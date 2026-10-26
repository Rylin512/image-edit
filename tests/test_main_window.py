from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QImage

from app.ui.main_window import MainWindow


def invert(image: QImage) -> QImage:
    image.invertPixels()
    return image


def test_window_starts_empty(window: MainWindow) -> None:
    assert window.document.is_empty
    assert window.windowTitle() == "Image Edit"
    assert not window.actions.action("file.save").isEnabled()
    assert not window.actions.action("view.zoom_in").isEnabled()


def test_load_path_updates_window(window: MainWindow, sample_image_path: Path) -> None:
    assert window.load_path(sample_image_path)

    assert not window.document.is_empty
    assert window.document.path == sample_image_path
    assert window.windowTitle().startswith("sample.png")
    assert window.canvas.has_image
    assert window.actions.action("file.save").isEnabled()
    assert window.actions.action("view.fit").isEnabled()


def test_operation_marks_modified_and_undo_cleans_it(
    window: MainWindow, sample_image_path: Path
) -> None:
    assert window.load_path(sample_image_path)

    assert window.apply_operation("反色", invert) is not None
    assert window.document.is_modified
    assert window.windowTitle().startswith("sample.png *")

    window.undo_stack.undo()
    assert not window.document.is_modified
    assert "*" not in window.windowTitle()


def test_save_to_writes_file(window: MainWindow, sample_image_path: Path, tmp_path: Path) -> None:
    assert window.load_path(sample_image_path)
    target = tmp_path / "output.png"

    assert window.save_to(target)
    assert target.is_file()
    assert window.document.path == target
    assert not window.document.is_modified
    assert window.windowTitle().startswith("output.png")
