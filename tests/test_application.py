from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_module_starts_and_exits_cleanly() -> None:
    """Exercise the real bootstrap (QApplication, logging, window) in a subprocess."""
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"

    result = subprocess.run(
        [sys.executable, "-m", "app", "--smoke-test"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
