from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QImage
from PySide6.QtWidgets import QFileDialog, QMessageBox

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


def test_save_to_rejects_unsupported_format(
    window: MainWindow, sample_image_path: Path, tmp_path: Path, monkeypatch
) -> None:
    assert window.load_path(sample_image_path)
    target = tmp_path / "output.txt"
    warnings: list[tuple] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args))

    assert not window.save_to(target)
    assert warnings
    assert not target.exists()


def test_undo_history_is_bounded(window: MainWindow) -> None:
    assert window.undo_stack.undoLimit() == MainWindow.UNDO_LIMIT


def test_load_path_asks_before_discarding_changes(
    window: MainWindow, sample_image_path: Path, tmp_path: Path, monkeypatch
) -> None:
    assert window.load_path(sample_image_path)
    assert window.apply_operation("反色", invert) is not None
    assert window.document.is_modified
    other = tmp_path / "other.png"
    assert window.document.image.save(str(other))

    monkeypatch.setattr(window, "_confirm_discard", lambda: False)
    assert not window.load_path(other)
    assert window.document.path == sample_image_path


def test_load_path_remembers_last_directory(
    window: MainWindow, sample_image_path: Path, settings
) -> None:
    assert window.load_path(sample_image_path)
    assert settings.value("files/last_directory", type=str) == str(sample_image_path.parent)


def test_dropped_path_finds_a_supported_local_file(
    window: MainWindow, sample_image_path: Path
) -> None:
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(sample_image_path))])
    event = QDragEnterEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    assert window._dropped_path(event) == sample_image_path


def test_drop_loads_a_supported_image(window: MainWindow, sample_image_path: Path) -> None:
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(sample_image_path))])
    event = QDropEvent(
        QPointF(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    window.dropEvent(event)
    assert event.isAccepted()
    assert window.document.path == sample_image_path


def test_close_with_unsaved_changes_can_be_cancelled(
    window: MainWindow, sample_image_path: Path, monkeypatch, qapp
) -> None:
    assert window.load_path(sample_image_path)
    assert window.apply_operation("反色", invert) is not None
    window.show()
    qapp.processEvents()
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Cancel,
    )

    assert not window.close()
    assert window.document.is_modified


def test_save_as_warns_before_dropping_alpha(
    window: MainWindow, tmp_path: Path, monkeypatch
) -> None:
    image = QImage(16, 16, QImage.Format.Format_ARGB32)
    image.fill(QColor(255, 0, 0, 128))
    source = tmp_path / "alpha.png"
    assert image.save(str(source))
    assert window.load_path(source)
    target = tmp_path / "alpha.jpg"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(target), "JPEG 图片 (*.jpg *.jpeg)"),
    )
    questions: list[tuple] = []

    def ask(*args, **kwargs):
        questions.append(args)
        return QMessageBox.StandardButton.Cancel

    monkeypatch.setattr(QMessageBox, "question", ask)

    assert not window.save_as()
    assert questions
    assert not target.exists()
    assert window.document.path == source
