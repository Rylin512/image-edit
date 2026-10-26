"""Allow ``python -m app`` and serve as the PyInstaller entry script."""

from app.main import main

if __name__ == "__main__":
    raise SystemExit(main())
