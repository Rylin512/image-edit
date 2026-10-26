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


def create_application(argv: list[str]) -> QApplication:
    """Create the QApplication with the settings Qt needs for QSettings."""
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
