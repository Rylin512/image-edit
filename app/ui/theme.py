"""Modern dark theme: palette, fonts, widget styles and native title bar."""

from __future__ import annotations

import logging
import sys

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QWidget

log = logging.getLogger(__name__)

ACCENT = "#5b8cff"
BACKGROUND = "#0f1115"

_STYLESHEET = """
QMainWindow, QDialog, QMessageBox {
    background-color: #0f1115;
}

QMenuBar {
    background-color: #15181e;
    color: #cbd3e1;
    padding: 4px 8px;
    spacing: 2px;
}
QMenuBar::item {
    background: transparent;
    padding: 6px 10px;
    border-radius: 6px;
}
QMenuBar::item:selected {
    background-color: #232833;
    color: #f0f3f8;
}
QMenuBar::item:pressed {
    background-color: #2b3242;
}

QMenu {
    background-color: #1a1e26;
    color: #dfe5ef;
    border: 1px solid #2c323e;
    border-radius: 8px;
    padding: 6px;
}
QMenu::item {
    background: transparent;
    padding: 7px 30px 7px 10px;
    border-radius: 5px;
}
QMenu::icon {
    left: 9px;
}
QMenu::item:selected {
    background-color: #2a3550;
    color: #ffffff;
}
QMenu::item:disabled {
    color: #697183;
}
QMenu::separator {
    height: 1px;
    background-color: #2a2f3a;
    margin: 5px 8px;
}

QToolBar#main_toolbar {
    background-color: #15181e;
    border: none;
    border-bottom: 1px solid #242a34;
    padding: 5px 10px;
    spacing: 3px;
}
QToolBar#main_toolbar::separator {
    width: 1px;
    background-color: #2a303b;
    margin: 5px 8px;
}
QToolButton {
    background: transparent;
    border: none;
    border-radius: 7px;
    padding: 5px;
    color: #ced6e4;
}
QToolButton:hover {
    background-color: #232833;
}
QToolButton:pressed {
    background-color: #2b3242;
}
QToolButton:checked {
    background-color: #26324a;
}
QToolButton:disabled {
    background-color: transparent;
}
QToolButton#crop_menu_button {
    padding: 5px 4px;
    border-radius: 6px;
}
QToolButton#crop_menu_button::menu-indicator {
    image: none;
    width: 0px;
    height: 0px;
}

QStatusBar {
    background-color: #15181e;
    border-top: 1px solid #242a34;
    color: #8c95a6;
}
QStatusBar::item {
    border: none;
}
QStatusBar QLabel {
    color: #8c95a6;
    padding: 0 10px;
}
QStatusBar QLabel#status_zoom {
    color: #b9ccff;
    background-color: #1a2233;
    border: 1px solid #27334c;
    border-radius: 8px;
    padding: 2px 10px;
    margin: 2px 2px 2px 8px;
}

QScrollBar:vertical {
    background: transparent;
    width: 11px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background-color: #333b49;
    min-height: 30px;
    border-radius: 3px;
}
QScrollBar::handle:vertical:hover {
    background-color: #424c5e;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background: transparent;
    border: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}

QScrollBar:horizontal {
    background: transparent;
    height: 11px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background-color: #333b49;
    min-width: 30px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #424c5e;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
    background: transparent;
    border: none;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
}

QToolTip {
    background-color: #1e222b;
    color: #e7eaf0;
    border: 1px solid #343b48;
    border-radius: 6px;
    padding: 5px 8px;
}

QPushButton {
    background-color: #242a35;
    color: #e2e7f0;
    border: 1px solid #343b48;
    border-radius: 7px;
    padding: 6px 16px;
    min-width: 70px;
}
QPushButton:hover {
    background-color: #2c3341;
    border-color: #414a5c;
}
QPushButton:pressed {
    background-color: #202630;
}
QPushButton:default {
    background-color: #3f6fd8;
    border-color: #5b8cff;
    color: #ffffff;
}
QPushButton:default:hover {
    background-color: #4c7ee8;
}
QPushButton:disabled {
    background-color: #1c2028;
    border-color: #272c36;
    color: #6b7283;
}
QPushButton#empty_open_button {
    background-color: #3f6fd8;
    border: 1px solid #6d97ff;
    border-radius: 9px;
    color: #ffffff;
    padding: 8px 22px;
    min-width: 0px;
    font-weight: 600;
}
QPushButton#empty_open_button:hover {
    background-color: #4d7ee8;
    border-color: #8cacff;
}
QPushButton#empty_open_button:pressed {
    background-color: #3560bf;
    border-color: #5b8cff;
}
QPushButton#crop_apply {
    background-color: #3f6fd8;
    border: 1px solid #6d97ff;
    border-radius: 8px;
    color: #ffffff;
    padding: 7px 18px;
    min-width: 84px;
    font-weight: 600;
}
QPushButton#crop_apply:hover {
    background-color: #4d7ee8;
    border-color: #8cacff;
}
QPushButton#crop_apply:pressed {
    background-color: #3560bf;
}
QPushButton#crop_cancel {
    background-color: rgba(18, 22, 30, 215);
    border: 1px solid #3a4354;
    border-radius: 8px;
    color: #dfe5ef;
    padding: 7px 16px;
    min-width: 64px;
}
QPushButton#crop_cancel:hover {
    background-color: #262d3a;
    border-color: #4a556a;
}

QMessageBox QLabel {
    color: #dfe5ef;
}
"""


def apply_theme(app: QApplication) -> None:
    """Apply the dark Fusion palette, UI font and stylesheet."""
    app.setStyle("Fusion")

    font = QFont()
    font.setFamilies(
        [
            "Segoe UI Variable Text",
            "Segoe UI Variable",
            "Microsoft YaHei UI",
            "Segoe UI",
        ]
    )
    font.setPointSize(10)
    app.setFont(font)

    window = QColor("#0f1115")
    surface = QColor("#15181e")
    base = QColor("#141820")
    button = QColor("#232833")
    text = QColor("#e7eaf0")
    muted = QColor("#8c95a6")
    accent = QColor(ACCENT)

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, window)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Base, base)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#191d25"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1e222b"))
    palette.setColor(QPalette.ColorRole.ToolTipText, text)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.Button, button)
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ff7a7a"))
    palette.setColor(QPalette.ColorRole.Highlight, accent)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Link, QColor("#7ea5ff"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#6f7787"))
    palette.setColor(QPalette.ColorRole.Light, QColor("#2a303b"))
    palette.setColor(QPalette.ColorRole.Midlight, QColor("#232833"))
    palette.setColor(QPalette.ColorRole.Mid, QColor("#1a1e26"))
    palette.setColor(QPalette.ColorRole.Dark, QColor("#0a0c10"))
    palette.setColor(QPalette.ColorRole.Shadow, QColor("#000000"))

    disabled = QColor("#697183")
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, disabled)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, surface)
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.HighlightedText,
        muted,
    )

    app.setPalette(palette)
    app.setStyleSheet(_STYLESHEET)


def enable_dark_title_bar(window: QWidget) -> None:
    """Ask Windows 10/11 to paint the native title bar in the app's colors."""
    if sys.platform != "win32":
        return

    try:
        import ctypes
        from ctypes import wintypes

        hwnd = wintypes.HWND(int(window.winId()))
        dwm = ctypes.windll.dwmapi

        def set_attribute(attribute: int, value: int) -> None:
            data = ctypes.c_int(value)
            dwm.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(data), ctypes.sizeof(data))

        set_attribute(20, 1)  # DWMWA_USE_IMMERSIVE_DARK_MODE
        set_attribute(35, 0x001E1815)  # DWMWA_CAPTION_COLOR, COLORREF #15181e
        set_attribute(36, 0x00F0EAE7)  # DWMWA_TEXT_COLOR, COLORREF #e7eaf0
        set_attribute(34, 0x003A2F2A)  # DWMWA_BORDER_COLOR, COLORREF #2a2f3a
    except Exception:  # pragma: no cover - only decorative, never fatal
        log.debug("Could not style the native title bar", exc_info=True)
