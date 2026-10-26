"""Process entry point.

Keeping bootstrap in a short module makes the packaged executable, the
``python -m app`` entry point and the tests share the same startup path.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QTimer

from app.application import create_application
from app.ui.main_window import MainWindow


def main(argv: list[str] | None = None) -> int:
    """Start the Qt event loop and return its exit code."""
    args = list(sys.argv if argv is None else argv)
    smoke_test = "--smoke-test" in args
    if smoke_test:
        args = [arg for arg in args if arg != "--smoke-test"]

    app = create_application(args)
    window = MainWindow()
    window.show()

    if smoke_test:
        # Used by packaging scripts to verify that a frozen build can boot.
        QTimer.singleShot(300, app.quit)

    return app.exec()
