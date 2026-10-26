from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QImage

from app.core.document import ImageDocument


def test_new_document_is_empty() -> None:
    document = ImageDocument()
    assert document.is_empty
    assert document.path is None
    assert not document.is_modified
    assert document.display_name == "未命名"


def test_load_sets_image_path_and_clean_state(sample_image_path: Path) -> None:
    document = ImageDocument()
    assert document.load(sample_image_path)

    assert not document.is_empty
    assert document.path == sample_image_path
    assert (document.image.width(), document.image.height()) == (48, 32)
    assert not document.is_modified
    assert document.display_name == "sample.png"


def test_load_missing_file_keeps_document_untouched(tmp_path: Path) -> None:
    document = ImageDocument()
    assert not document.load(tmp_path / "missing.png")
    assert document.is_empty
    assert document.path is None


def test_replace_image_marks_document_modified(sample_image: QImage) -> None:
    document = ImageDocument()
    document.replace_image(sample_image)
    assert not document.is_empty
    assert document.is_modified


def test_replace_with_empty_image_raises() -> None:
    document = ImageDocument()
    with pytest.raises(ValueError):
        document.replace_image(QImage())


def test_save_roundtrip_updates_path(sample_image_path: Path, tmp_path: Path) -> None:
    document = ImageDocument()
    assert document.load(sample_image_path)

    target = tmp_path / "copy.png"
    assert document.save(target)
    assert document.path == target
    assert not document.is_modified

    saved = QImage()
    assert saved.load(str(target))


def test_save_jpeg_roundtrip(sample_image_path: Path, tmp_path: Path) -> None:
    document = ImageDocument()
    assert document.load(sample_image_path)
    target = tmp_path / "copy.jpg"

    assert document.save(target)
    assert document.path == target
    saved = QImage()
    assert saved.load(str(target))


def test_save_unsupported_format_keeps_existing_file(
    sample_image_path: Path, tmp_path: Path
) -> None:
    document = ImageDocument()
    assert document.load(sample_image_path)
    target = tmp_path / "notes.txt"
    target.write_bytes(b"keep me")

    assert not document.save(target)
    assert target.read_bytes() == b"keep me"
    assert document.path == sample_image_path


def test_save_without_path_returns_false(sample_image: QImage) -> None:
    document = ImageDocument()
    document.replace_image(sample_image)
    assert not document.save()


def test_save_empty_document_returns_false(tmp_path: Path) -> None:
    assert not ImageDocument().save(tmp_path / "empty.png")


def test_load_emits_signals(qapp, sample_image_path: Path) -> None:
    document = ImageDocument()
    events: list[str] = []
    document.imageChanged.connect(lambda: events.append("image"))
    document.pathChanged.connect(lambda path: events.append("path"))
    document.modifiedChanged.connect(lambda modified: events.append("modified"))

    assert document.load(sample_image_path)
    assert "image" in events
    assert "path" in events
