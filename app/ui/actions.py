"""A tiny registry that keeps menu, toolbar and shortcut wiring declarative."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMenu, QMenuBar, QToolBar, QWidget

from app.ui.icons import make_icon

Shortcut = QKeySequence | QKeySequence.StandardKey | str
Slot = Callable[[], object]


class ActionRegistry:
    """Creates and stores QActions so features can add entries without bloat."""

    def __init__(self, parent: QWidget) -> None:
        self._parent = parent
        self._actions: dict[str, QAction] = {}
        self._menus: dict[str, QMenu] = {}

    def create(
        self,
        key: str,
        text: str,
        *,
        slot: Slot | None = None,
        shortcut: Shortcut | None = None,
        status_tip: str = "",
        icon_text: str | None = None,
        icon: str | None = None,
        checkable: bool = False,
    ) -> QAction:
        """Create and remember an action under ``key``."""
        if key in self._actions:
            raise KeyError(f"Action already registered: {key}")

        action = QAction(text, self._parent)
        if slot is not None:
            action.triggered.connect(slot)
        if shortcut is not None:
            action.setShortcut(QKeySequence(shortcut) if isinstance(shortcut, str) else shortcut)
        if status_tip:
            action.setStatusTip(status_tip)
        if icon_text:
            action.setIconText(icon_text)
        if icon:
            action.setIcon(make_icon(icon))
            hint = action.shortcut().toString(QKeySequence.SequenceFormat.NativeText)
            tip = status_tip or action.iconText()
            action.setToolTip(f"{tip}  ({hint})" if hint else tip)
        action.setCheckable(checkable)
        self._actions[key] = action
        return action

    def register(self, key: str, action: QAction) -> QAction:
        """Register an action created elsewhere, such as QAction from QUndoStack."""
        if key in self._actions:
            raise KeyError(f"Action already registered: {key}")
        self._actions[key] = action
        return action

    def action(self, key: str) -> QAction:
        return self._actions[key]

    def create_menu(self, key: str, title: str, menubar: QMenuBar) -> QMenu:
        if key in self._menus:
            raise KeyError(f"Menu already created: {key}")
        menu = menubar.addMenu(title)
        self._menus[key] = menu
        return menu

    def add(self, menu_key: str, *action_keys: str) -> None:
        menu = self._menus[menu_key]
        for key in action_keys:
            menu.addAction(self._actions[key])

    def add_separator(self, menu_key: str) -> None:
        self._menus[menu_key].addSeparator()

    def add_to_toolbar(self, toolbar: QToolBar, *action_keys: str) -> None:
        for key in action_keys:
            toolbar.addAction(self._actions[key])
