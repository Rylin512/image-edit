from __future__ import annotations

from pathlib import Path

from app.utils.files import is_supported_image, save_format_for_path, suffix_from_filter


def test_suffix_from_filter() -> None:
    assert suffix_from_filter("PNG 图片 (*.png)") == ".png"
    assert suffix_from_filter("JPEG 图片 (*.jpg *.jpeg)") == ".jpg"
    assert suffix_from_filter("WebP 图片 (*.webp)") == ".webp"
    assert suffix_from_filter("未知过滤器") == ".png"


def test_is_supported_image() -> None:
    assert is_supported_image("photo.PNG")
    assert is_supported_image("photo.jpeg")
    assert is_supported_image("photo.webp")
    assert not is_supported_image("notes.txt")
    assert not is_supported_image("archive.zip")


def test_save_format_for_path() -> None:
    assert save_format_for_path("photo.png") == "png"
    assert save_format_for_path(Path("photo.JPG")) == "jpeg"
    assert save_format_for_path("photo.jpeg") == "jpeg"
    assert save_format_for_path("photo.tif") == "tiff"
    assert save_format_for_path("notes.txt") is None
    assert save_format_for_path("no_extension") is None
