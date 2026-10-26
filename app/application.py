"""QApplication bootstrap: identity, logging, theme and exception handling."""

from __future__ import annotations

import logging
import sys
import traceback

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication, QMessageBox

from app import __version__
from app.ui.theme import apply_theme
from app.utils.logging import setup_logging
from app.utils.paths import app_data_dir

APP_NAME = "ImageEdit"
ORG_NAME = "Rylin512"
MIN_PYTHON = (3, 12)


def ensure_supported_python(version_info: tuple[int, ...] | None = None) -> None:
    """Fail early with a readable message on an unsupported interpreter."""
    info = sys.version_info if version_info is None else version_info
    if info < MIN_PYTHON:
        found = ".".join(str(part) for part in info[:2])
        raise SystemExit(f"Image Edit 需要 Python 3.12 或更高版本（当前为 {found}）。")


def create_application(argv: list[str]) -> QApplication:
    """Create the QApplication with the settings Qt needs for QSettings."""
    ensure_supported_python()
    QCoreApplication.setOrganizationName(ORG_NAME)
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setApplicationVersion(__version__)

    app = QApplication(argv)
    app.setApplicationDisplayName("Image Edit")
    setup_logging()
    install_exception_hook()
    apply_theme(app)
    logging.getLogger(__name__).info("Image Edit %s starting", __version__)
    return app


def install_exception_hook() -> None:
    """Log unhandled exceptions instead of silently terminating the process."""

    def handle(exc_type, exc, tb) -> None:
        logging.getLogger("image_edit").critical(
            "Unhandled exception", exc_info=(exc_type, exc, tb)
        )
        detail = "".join(traceback.format_exception(exc_type, exc, tb))
        log_file = app_data_dir() / "logs" / "app.log"
        QMessageBox.critical(
            None,
            "程序错误",
            f"发生未处理的错误：\n\n{exc}\n\n详细信息已写入：\n{log_file}\n\n{detail}",
        )

    sys.excepthook = handle
