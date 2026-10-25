import os

# Keep PySide6 headless on CI and in other environments without a display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
