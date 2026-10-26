"""Prepare the local virtual environment and launch the desktop app.

Run through ``run.bat`` (Windows) or ``python scripts/launch.py``. The first
run creates ``.venv`` and installs dependencies; later runs only reinstall when
``requirements.txt`` changes.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
STAMP = VENV_DIR / ".requirements.sha256"


def venv_python() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def venv_pythonw() -> Path:
    if sys.platform == "win32":
        windowless = VENV_DIR / "Scripts" / "pythonw.exe"
        if windowless.is_file():
            return windowless
    return venv_python()


def requirements_digest() -> str:
    digest = hashlib.sha256()
    if REQUIREMENTS.is_file():
        digest.update(REQUIREMENTS.read_bytes())
    return digest.hexdigest()


def ensure_environment() -> Path:
    python = venv_python()
    if not python.is_file():
        print("First run: creating the virtual environment...")
        venv.EnvBuilder(with_pip=True).create(VENV_DIR)
        python = venv_python()
    if not python.is_file():
        raise SystemExit("Could not create the virtual environment.")

    wanted = requirements_digest()
    installed = STAMP.read_text(encoding="utf-8").strip() if STAMP.is_file() else ""
    if installed != wanted:
        print("Installing dependencies (the first run can take a few minutes)...")
        subprocess.run(
            [str(python), "-m", "pip", "install", "--upgrade", "pip"],
            check=True,
        )
        subprocess.run(
            [str(python), "-m", "pip", "install", "-r", str(REQUIREMENTS)],
            check=True,
        )
        STAMP.write_text(wanted, encoding="utf-8")
        print("Dependencies are ready.")

    return python


def launch() -> int:
    ensure_environment()
    arguments = sys.argv[1:]

    if "--prepare-only" in arguments:
        print("Environment is ready.")
        return 0

    # --console keeps a terminal attached for debugging; --smoke-test is
    # forwarded to the app so this path can be verified non-interactively.
    console = "--console" in arguments
    app_arguments = [
        argument for argument in arguments if argument not in {"--console", "--prepare-only"}
    ]
    executable = venv_python() if console else venv_pythonw()

    command = [str(executable), "-m", "app", *app_arguments]
    if console:
        return subprocess.call(command, cwd=ROOT)

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    subprocess.Popen(
        command,
        cwd=ROOT,
        creationflags=creationflags,
        close_fds=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(launch())
