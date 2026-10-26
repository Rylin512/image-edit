from __future__ import annotations

import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QImage

from app.core.image_ops import (
    crop_image,
    flip_horizontal,
    flip_vertical,
    rotate_180,
    rotate_left,
    rotate_right,
)


def make_marked_image() -> QImage:
    """A 3x2 image whose six pixels all have distinct colors."""
    image = QImage(3, 2, QImage.Format.Format_RGB32)
    colors = (
        ((0, 0), "#ff0000"),
        ((1, 0), "#00ff00"),
        ((2, 0), "#0000ff"),
        ((0, 1), "#ffff00"),
        ((1, 1), "#ff00ff"),
        ((2, 1), "#00ffff"),
    )
    for (x, y), color in colors:
        image.setPixelColor(x, y, QColor(color))
    return image


def rows(image: QImage) -> list[list[str]]:
    return [
        [image.pixelColor(x, y).name() for x in range(image.width())] for y in range(image.height())
    ]


def test_rotate_right_moves_the_top_row_to_the_right_column() -> None:
    result = rotate_right(make_marked_image())

    assert (result.width(), result.height()) == (2, 3)
    assert rows(result) == [
        ["#ffff00", "#ff0000"],
        ["#ff00ff", "#00ff00"],
        ["#00ffff", "#0000ff"],
    ]


def test_rotate_left_is_the_inverse_of_rotate_right() -> None:
    original = make_marked_image()
    assert rows(rotate_left(rotate_right(original))) == rows(original)

    result = rotate_left(original)
    assert (result.width(), result.height()) == (2, 3)
    assert rows(result) == [
        ["#0000ff", "#00ffff"],
        ["#00ff00", "#ff00ff"],
        ["#ff0000", "#ffff00"],
    ]


def test_rotate_180_turns_the_image_upside_down() -> None:
    result = rotate_180(make_marked_image())

    assert rows(result) == [
        ["#00ffff", "#ff00ff", "#ffff00"],
        ["#0000ff", "#00ff00", "#ff0000"],
    ]


def test_flip_horizontal_and_vertical_mirror_the_expected_axis() -> None:
    original = make_marked_image()

    assert rows(flip_horizontal(original)) == [
        ["#0000ff", "#00ff00", "#ff0000"],
        ["#00ffff", "#ff00ff", "#ffff00"],
    ]
    assert rows(flip_vertical(original)) == [
        ["#ffff00", "#ff00ff", "#00ffff"],
        ["#ff0000", "#00ff00", "#0000ff"],
    ]


def test_crop_clips_the_selection_to_the_image() -> None:
    result = crop_image(make_marked_image(), QRect(1, 0, 2, 3))

    assert (result.width(), result.height()) == (2, 2)
    assert rows(result) == [
        ["#00ff00", "#0000ff"],
        ["#ff00ff", "#00ffff"],
    ]
    clipped = crop_image(make_marked_image(), QRect(-4, -4, 5, 5))
    assert (clipped.width(), clipped.height()) == (1, 1)


def test_crop_rejects_an_empty_or_null_image() -> None:
    image = make_marked_image()
    with pytest.raises(ValueError):
        crop_image(image, QRect(20, 20, 5, 5))
    with pytest.raises(ValueError):
        crop_image(QImage(), QRect(0, 0, 1, 1))
