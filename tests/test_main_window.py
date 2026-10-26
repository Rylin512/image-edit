from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMimeData, QPoint, QPointF, QRect, Qt, QUrl
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFileDialog, QMessageBox, QToolButton

from app.ui.crop import CropOverlay
from app.ui.main_window import MainWindow


def invert(image: QImage) -> QImage:
    image.invertPixels()
    return image


def test_window_starts_empty(window: MainWindow) -> None:
    assert window.document.is_empty
    assert window.windowTitle() == "Image Edit"
    assert not window.actions.action("file.save").isEnabled()
    assert not window.actions.action("view.zoom_in").isEnabled()
    assert not window.actions.action("image.rotate_right").isEnabled()
    assert not window.actions.action("image.crop.free").isEnabled()
    assert not window.actions.action("image.crop.16_9").isEnabled()
    crop_menu_button = window.findChild(QToolButton, "crop_menu_button")
    assert crop_menu_button is not None
    assert not crop_menu_button.isEnabled()


def test_load_path_updates_window(window: MainWindow, sample_image_path: Path) -> None:
    assert window.load_path(sample_image_path)

    assert not window.document.is_empty
    assert window.document.path == sample_image_path
    assert window.windowTitle().startswith("sample.png")
    assert window.canvas.has_image
    assert window.actions.action("file.save").isEnabled()
    assert window.actions.action("view.fit").isEnabled()
    assert window.actions.action("image.rotate_right").isEnabled()
    assert window.actions.action("image.crop.free").isEnabled()
    assert window.actions.action("image.crop.16_9").isEnabled()
    crop_menu_button = window.findChild(QToolButton, "crop_menu_button")
    assert crop_menu_button is not None
    assert crop_menu_button.isEnabled()


def test_free_and_ratio_crops_share_one_submenu(window: MainWindow) -> None:
    crop_menu = window.actions.menu("image.crop")

    labels = [action.text() for action in crop_menu.actions() if not action.isSeparator()]
    assert labels[0] == "自由裁剪(&F)"
    assert labels[1:] == [
        "1:1 方形",
        "4:3 横向",
        "3:4 竖向",
        "3:2 横向",
        "2:3 竖向",
        "16:9 宽屏",
        "9:16 竖屏",
    ]
    button = window.findChild(QToolButton, "crop_menu_button")
    assert button is not None
    toolbar_menu = button.menu()
    assert toolbar_menu is not None
    assert [
        action.text() for action in toolbar_menu.actions() if not action.isSeparator()
    ] == labels


def test_rotate_action_is_undoable(window: MainWindow, sample_image_path: Path) -> None:
    assert window.load_path(sample_image_path)

    window.actions.action("image.rotate_right").trigger()

    assert (window.document.image.width(), window.document.image.height()) == (32, 48)
    assert window.document.is_modified
    window.undo_stack.undo()
    assert (window.document.image.width(), window.document.image.height()) == (48, 32)


def test_square_crop_action_locks_the_ratio_and_applies(
    window: MainWindow, sample_image_path: Path, qapp
) -> None:
    assert window.load_path(sample_image_path)
    window.show()
    qapp.processEvents()

    window.actions.action("image.crop.1_1").trigger()
    qapp.processEvents()

    assert window.canvas.is_cropping
    assert window.canvas.crop_rect() == QRect(8, 0, 32, 32)

    overlay = window.canvas.findChild(CropOverlay)
    assert overlay is not None
    handle = window.canvas.image_to_view(QPointF(40.0, 32.0)).toPoint()
    target = handle - QPoint(8, 4)
    QTest.mousePress(overlay, Qt.MouseButton.LeftButton, pos=handle)
    QTest.mouseMove(overlay, target, delay=10)
    QTest.mouseRelease(overlay, Qt.MouseButton.LeftButton, pos=target)

    rect = window.canvas.crop_rect()
    assert rect.width() == rect.height()
    assert 0 < rect.width() < 32

    window.canvas.accept_crop()
    assert (window.document.image.width(), window.document.image.height()) == (
        rect.width(),
        rect.height(),
    )
    assert window.document.is_modified
    window.undo_stack.undo()
    assert (window.document.image.width(), window.document.image.height()) == (48, 32)


def test_crop_signal_applies_an_undoable_crop(window: MainWindow, sample_image_path: Path) -> None:
    assert window.load_path(sample_image_path)

    window.canvas.cropAccepted.emit(QRect(10, 5, 20, 15))

    assert (window.document.image.width(), window.document.image.height()) == (20, 15)
    assert window.document.is_modified
    window.undo_stack.undo()
    assert (window.document.image.width(), window.document.image.height()) == (48, 32)


def test_crop_that_covers_the_whole_image_is_a_no_op(
    window: MainWindow, sample_image_path: Path
) -> None:
    assert window.load_path(sample_image_path)

    window.canvas.cropAccepted.emit(QRect(0, 0, 48, 32))

    assert not window.document.is_modified
    assert window.undo_stack.count() == 0


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
