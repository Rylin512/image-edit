"""Main window: document wiring, menus, actions, status bar and persistence."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QByteArray, QRect, QSettings, QSize, Qt
from PySide6.QtGui import (
    QCloseEvent,
    QDragEnterEvent,
    QDropEvent,
    QIcon,
    QImage,
    QKeySequence,
    QUndoStack,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QToolBar,
    QToolButton,
)

from app import __version__
from app.core.commands import ImageOperationCommand, apply_image_operation
from app.core.document import ImageDocument
from app.core.image_ops import (
    crop_image,
    flip_horizontal,
    flip_vertical,
    rotate_180,
    rotate_left,
    rotate_right,
)
from app.ui.actions import ActionRegistry
from app.ui.canvas import CanvasView
from app.ui.icons import make_icon
from app.ui.theme import enable_dark_title_bar
from app.utils.files import (
    IMAGE_OPEN_FILTER,
    IMAGE_SAVE_FILTER,
    is_supported_image,
    save_format_for_path,
    suffix_from_filter,
)
from app.utils.paths import resource_path

# Key, menu label, width / height. Keeping the presets in one place lets the
# crop menu and the toolbar drop-down stay in sync.
CROP_RATIOS: tuple[tuple[str, str, float], ...] = (
    ("image.crop.1_1", "1:1 方形", 1.0),
    ("image.crop.4_3", "4:3 横向", 4.0 / 3.0),
    ("image.crop.3_4", "3:4 竖向", 3.0 / 4.0),
    ("image.crop.3_2", "3:2 横向", 3.0 / 2.0),
    ("image.crop.2_3", "2:3 竖向", 2.0 / 3.0),
    ("image.crop.16_9", "16:9 宽屏", 16.0 / 9.0),
    ("image.crop.9_16", "9:16 竖屏", 9.0 / 16.0),
)


class MainWindow(QMainWindow):
    """Shell that owns the document, undo stack and canvas."""

    UNDO_LIMIT = 20

    def __init__(self, settings: QSettings | None = None) -> None:
        super().__init__()
        self._settings = settings or QSettings()
        self._document = ImageDocument(self)
        self._undo_stack = QUndoStack(self)
        self._undo_stack.setUndoLimit(self.UNDO_LIMIT)
        self._actions = ActionRegistry(self)
        self._titlebar_themed = False
        self._crop_menu_button: QToolButton | None = None

        self.setMinimumSize(760, 500)
        self._canvas = CanvasView(self)
        self.setCentralWidget(self._canvas)
        self.setAcceptDrops(True)
        self._install_icon()

        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_status_bar()
        self._connect_signals()
        self._restore_window_state()

        self._update_title()
        self._update_document_labels()
        self._update_action_states()
        self.statusBar().showMessage("就绪", 4000)

    # -- public API used by feature modules and tests --------------------
    @property
    def document(self) -> ImageDocument:
        return self._document

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack

    @property
    def canvas(self) -> CanvasView:
        return self._canvas

    @property
    def actions(self) -> ActionRegistry:
        return self._actions

    def apply_operation(
        self, text: str, operation: Callable[[QImage], QImage]
    ) -> ImageOperationCommand | None:
        """Run an undoable operation on the current image."""
        command = apply_image_operation(self._document, self._undo_stack, text, operation)
        if command is None:
            self.statusBar().showMessage("请先打开一张图片", 3000)
        return command

    def load_path(self, path: str | Path) -> bool:
        """Load a file into the window, asking before discarding edits."""
        if not self._confirm_discard():
            return False
        return self._load_path_unchecked(path)

    def _load_path_unchecked(self, path: str | Path) -> bool:
        """Load a file after the caller has already handled unsaved changes."""
        target = Path(path)
        if not self._document.load(target):
            QMessageBox.warning(self, "打开失败", f"无法打开图片：\n{target}")
            return False

        self._undo_stack.clear()
        self._canvas.reset_view()
        self._canvas.animate_image_in()
        self._canvas.setFocus()
        self._remember_directory(target)
        self.statusBar().showMessage(f"已打开 {target.name}", 5000)
        return True

    def save_to(self, path: str | Path) -> bool:
        """Save to an explicit path, reporting failures to the user."""
        if self._document.is_empty:
            return False

        target = Path(path)
        if save_format_for_path(target) is None:
            QMessageBox.warning(
                self,
                "保存失败",
                f"不支持的文件格式：\n{target}\n\n请使用 PNG、JPEG、WebP、BMP 或 TIFF。",
            )
            return False
        if not self._document.save(target):
            QMessageBox.warning(self, "保存失败", f"无法写入文件：\n{target}")
            return False

        self._undo_stack.setClean()
        self._document.set_modified(False)
        self._remember_directory(target)
        self.statusBar().showMessage(f"已保存 {target.name}", 5000)
        return True

    def save(self) -> bool:
        if self._document.is_empty:
            return False
        if self._document.path is None:
            return self.save_as()
        if not self._confirm_jpeg_alpha(self._document.path):
            return False
        return self.save_to(self._document.path)

    def save_as(self) -> bool:
        if self._document.is_empty:
            return False

        if self._document.path is not None:
            start = self._document.path
        else:
            start = self._last_directory() / "未命名.png"

        path, selected_filter = QFileDialog.getSaveFileName(
            self, "保存图片", str(start), IMAGE_SAVE_FILTER
        )
        if not path:
            return False

        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(suffix_from_filter(selected_filter))
        if not self._confirm_jpeg_alpha(target):
            return False
        return self.save_to(target)

    def _confirm_jpeg_alpha(self, target: Path) -> bool:
        """Warn before flattening transparency into a JPEG."""
        if target.suffix.lower() not in {".jpg", ".jpeg"}:
            return True
        if not self._document.image.hasAlphaChannel():
            return True

        answer = QMessageBox.question(
            self,
            "JPEG 透明通道",
            "JPEG 不支持透明通道，透明区域会丢失。\n是否仍要保存？",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        return answer == QMessageBox.StandardButton.Save

    def open_image(self) -> None:
        if not self._confirm_discard():
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "打开图片", str(self._last_directory()), IMAGE_OPEN_FILTER
        )
        if path:
            self._load_path_unchecked(path)

    # -- construction ----------------------------------------------------
    def _install_icon(self) -> None:
        # Prefer the multi-size ICO: Windows picks a native 16px image for the
        # title bar/taskbar instead of downscaling a single large PNG.
        icon_path = resource_path("app", "resources", "icon.ico")
        if not icon_path.is_file():
            icon_path = resource_path("app", "resources", "icon.png")
        if icon_path.is_file():
            icon = QIcon(str(icon_path))
            self.setWindowIcon(icon)
            app = QApplication.instance()
            if app is not None:
                app.setWindowIcon(icon)

    def _build_actions(self) -> None:
        registry = self._actions

        registry.create(
            "file.open",
            "打开(&O)…",
            slot=self.open_image,
            shortcut=QKeySequence.StandardKey.Open,
            status_tip="打开图片",
            icon_text="打开",
            icon="open",
        )
        registry.create(
            "file.save",
            "保存(&S)",
            slot=self.save,
            shortcut=QKeySequence.StandardKey.Save,
            status_tip="保存图片",
            icon_text="保存",
            icon="save",
        )
        registry.create(
            "file.save_as",
            "另存为(&A)…",
            slot=self.save_as,
            shortcut=QKeySequence.StandardKey.SaveAs,
            status_tip="保存到新文件",
            icon_text="另存为",
            icon="save_as",
        )
        registry.create(
            "file.exit",
            "退出(&Q)",
            slot=self.close,
            shortcut=QKeySequence.StandardKey.Quit,
            status_tip="退出程序",
        )

        undo = self._undo_stack.createUndoAction(self, "撤销")
        undo.setShortcut(QKeySequence.StandardKey.Undo)
        undo.setIconText("撤销")
        undo.setIcon(make_icon("undo"))
        undo.setToolTip("撤销  (Ctrl+Z)")
        registry.register("edit.undo", undo)

        redo = self._undo_stack.createRedoAction(self, "重做")
        redo.setShortcut(QKeySequence.StandardKey.Redo)
        redo.setIconText("重做")
        redo.setIcon(make_icon("redo"))
        redo.setToolTip("重做  (Ctrl+Y)")
        registry.register("edit.redo", redo)

        registry.create(
            "image.rotate_left",
            "向左旋转 90°",
            slot=lambda: self._apply_transform("向左旋转 90°", rotate_left),
            shortcut=QKeySequence("Ctrl+Alt+L"),
            status_tip="将图像逆时针旋转 90°",
            icon_text="左旋",
            icon="rotate_left",
        )
        registry.create(
            "image.rotate_right",
            "向右旋转 90°",
            slot=lambda: self._apply_transform("向右旋转 90°", rotate_right),
            shortcut=QKeySequence("Ctrl+Alt+R"),
            status_tip="将图像顺时针旋转 90°",
            icon_text="右旋",
            icon="rotate_right",
        )
        registry.create(
            "image.rotate_180",
            "旋转 180°",
            slot=lambda: self._apply_transform("旋转 180°", rotate_180),
            status_tip="将图像旋转半圈",
        )
        registry.create(
            "image.flip_horizontal",
            "水平镜像",
            slot=lambda: self._apply_transform("水平镜像", flip_horizontal),
            shortcut=QKeySequence("Ctrl+Alt+H"),
            status_tip="沿垂直轴镜像图像",
            icon_text="水平镜像",
            icon="flip_horizontal",
        )
        registry.create(
            "image.flip_vertical",
            "垂直镜像",
            slot=lambda: self._apply_transform("垂直镜像", flip_vertical),
            shortcut=QKeySequence("Ctrl+Alt+V"),
            status_tip="沿水平轴镜像图像",
            icon_text="垂直镜像",
            icon="flip_vertical",
        )

        registry.create(
            "image.crop.free",
            "自由裁剪(&F)",
            slot=lambda: self._begin_crop(None),
            shortcut="C",
            status_tip="拖动选择裁剪区域",
            icon_text="裁剪",
            icon="crop",
        )
        for key, label, ratio in CROP_RATIOS:
            registry.create(
                key,
                label,
                # QAction.triggered(bool) supplies the checked flag, so consume
                # it explicitly; otherwise it would overwrite the captured ratio
                # and start the crop with an aspect of 0.
                slot=lambda _checked=False, aspect=ratio: self._begin_crop(aspect),
                status_tip=f"按 {label} 比例裁剪",
            )

        registry.create(
            "view.zoom_in",
            "放大",
            slot=self._zoom_in,
            shortcut=QKeySequence.StandardKey.ZoomIn,
            status_tip="放大画布",
            icon_text="放大",
            icon="zoom_in",
        )
        registry.create(
            "view.zoom_out",
            "缩小",
            slot=self._zoom_out,
            shortcut=QKeySequence.StandardKey.ZoomOut,
            status_tip="缩小画布",
            icon_text="缩小",
            icon="zoom_out",
        )
        registry.create(
            "view.actual_size",
            "实际大小",
            slot=self._actual_size,
            shortcut=QKeySequence("Ctrl+1"),
            status_tip="按 100% 显示",
            icon="actual",
        )
        registry.create(
            "view.fit",
            "适应窗口",
            slot=self._fit_to_window,
            shortcut=QKeySequence("Ctrl+0"),
            status_tip="缩放以适合窗口",
            icon_text="适应",
            icon="fit",
        )
        registry.create(
            "help.about",
            "关于 Image Edit",
            slot=self._show_about,
            status_tip="关于本程序",
        )

    def _build_menus(self) -> None:
        registry = self._actions
        menubar = self.menuBar()

        registry.create_menu("file", "文件(&F)", menubar)
        registry.add("file", "file.open")
        registry.add("file", "file.save", "file.save_as")
        registry.add_separator("file")
        registry.add("file", "file.exit")

        registry.create_menu("edit", "编辑(&E)", menubar)
        registry.add("edit", "edit.undo", "edit.redo")

        image_menu = registry.create_menu("image", "图像(&I)", menubar)
        registry.create_submenu("image.rotate", "旋转", image_menu)
        registry.add("image.rotate", "image.rotate_left", "image.rotate_right", "image.rotate_180")
        registry.create_submenu("image.mirror", "镜像", image_menu)
        registry.add("image.mirror", "image.flip_horizontal", "image.flip_vertical")

        registry.create_submenu("image.crop", "裁剪", image_menu)
        registry.add("image.crop", "image.crop.free")
        registry.add_separator("image.crop")
        registry.add("image.crop", *(key for key, _, _ in CROP_RATIOS))

        registry.create_menu("view", "视图(&V)", menubar)
        registry.add("view", "view.zoom_in", "view.zoom_out")
        registry.add_separator("view")
        registry.add("view", "view.actual_size", "view.fit")

        registry.create_menu("help", "帮助(&H)", menubar)
        registry.add("help", "help.about")

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("主工具栏", self)
        toolbar.setObjectName("main_toolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QSize(22, 22))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)

        self._actions.add_to_toolbar(toolbar, "file.open", "file.save")
        toolbar.addSeparator()
        self._actions.add_to_toolbar(toolbar, "edit.undo", "edit.redo")
        toolbar.addSeparator()
        self._actions.add_to_toolbar(
            toolbar,
            "image.rotate_left",
            "image.rotate_right",
            "image.flip_horizontal",
            "image.flip_vertical",
        )
        self._add_crop_button(toolbar)
        toolbar.addSeparator()
        self._actions.add_to_toolbar(toolbar, "view.zoom_out", "view.zoom_in", "view.fit")
        self.addToolBar(toolbar)

    def _add_crop_button(self, toolbar: QToolBar) -> None:
        """A free-crop button plus a separate ratio menu button.

        Qt's MenuButtonPopup squeezes the icon and menu indicator into one
        native control, which clipped the crop glyph at this toolbar size.
        Two adjacent buttons keep both hit areas clear.
        """
        self._actions.add_to_toolbar(toolbar, "image.crop.free")

        menu = QMenu(self)
        menu.addAction(self._actions.action("image.crop.free"))
        menu.addSeparator()
        for key, _, _ in CROP_RATIOS:
            menu.addAction(self._actions.action(key))

        button = QToolButton(toolbar)
        button.setObjectName("crop_menu_button")
        button.setIcon(make_icon("chevron_down"))
        button.setIconSize(QSize(12, 12))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setMenu(menu)
        button.setFixedSize(22, 32)
        button.setToolTip("选择常用裁剪比例")
        toolbar.addWidget(button)
        self._crop_menu_button = button

    def _build_status_bar(self) -> None:
        self._cursor_label = QLabel("")
        self._cursor_label.setObjectName("status_cursor")
        self._cursor_label.setMinimumWidth(110)
        self._size_label = QLabel("")
        self._size_label.setObjectName("status_size")
        self._size_label.setMinimumWidth(90)
        self._zoom_label = QLabel("")
        self._zoom_label.setObjectName("status_zoom")
        self._zoom_label.setMinimumWidth(92)
        self._zoom_label.setVisible(False)

        bar = self.statusBar()
        bar.setSizeGripEnabled(False)
        bar.setContentsMargins(6, 0, 6, 0)
        bar.addPermanentWidget(self._cursor_label)
        bar.addPermanentWidget(self._size_label)
        bar.addPermanentWidget(self._zoom_label)

    def _connect_signals(self) -> None:
        self._document.imageChanged.connect(self._on_image_changed)
        self._document.pathChanged.connect(self._update_title)
        self._document.modifiedChanged.connect(self._update_title)
        self._undo_stack.cleanChanged.connect(self._on_clean_changed)
        self._canvas.zoomChanged.connect(self._on_zoom_changed)
        self._canvas.cursorPositionChanged.connect(self._on_cursor_changed)
        self._canvas.openRequested.connect(self.open_image)
        self._canvas.cropAccepted.connect(self._on_crop_accepted)
        self._canvas.cropCancelled.connect(self._on_crop_cancelled)

    # -- signal handlers -------------------------------------------------
    def _on_image_changed(self) -> None:
        self._canvas.set_image(self._document.image, reset_view=False)
        self._update_document_labels()
        self._update_action_states()
        self._update_title()

    def _on_clean_changed(self, clean: bool) -> None:
        self._document.set_modified(not clean)

    def _on_zoom_changed(self, percent: float) -> None:
        self._zoom_label.setVisible(percent > 0)
        self._zoom_label.setText(f"缩放 {percent:.0f}%" if percent > 0 else "")

    def _on_cursor_changed(self, position) -> None:
        if position is None:
            self._cursor_label.setText("")
            return
        self._cursor_label.setText(f"x {int(position.x())}, y {int(position.y())}")

    # -- view actions ----------------------------------------------------
    def _zoom_in(self) -> None:
        self._canvas.zoom_in()

    def _zoom_out(self) -> None:
        self._canvas.zoom_out()

    def _actual_size(self) -> None:
        self._canvas.actual_size()

    def _fit_to_window(self) -> None:
        self._canvas.fit_to_window()

    # -- image actions ---------------------------------------------------
    def _apply_transform(self, text: str, operation: Callable[[QImage], QImage]) -> None:
        if self.apply_operation(text, operation) is not None:
            self.statusBar().showMessage(f"{text}完成", 2500)

    def _begin_crop(self, aspect_ratio: float | None) -> None:
        if self._document.is_empty:
            self.statusBar().showMessage("请先打开一张图片", 3000)
            return
        self._canvas.begin_crop(aspect_ratio)
        self.statusBar().showMessage(
            "拖动裁剪框，按 Enter 应用，Esc 取消",
            6000,
        )

    def _on_crop_accepted(self, rect: QRect) -> None:
        image = self._document.image
        target = rect.normalized().intersected(image.rect())
        if target.isEmpty():
            self.statusBar().showMessage("裁剪区域无效", 3000)
            return
        if target == image.rect():
            self.statusBar().showMessage("裁剪区域与图像相同，未做修改", 3000)
            return
        if self.apply_operation("裁剪", lambda source: crop_image(source, target)) is not None:
            self.statusBar().showMessage(
                f"已裁剪为 {target.width()} × {target.height()}",
                4000,
            )

    def _on_crop_cancelled(self) -> None:
        self.statusBar().showMessage("已取消裁剪", 2500)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "关于 Image Edit",
            f"<h3>Image Edit {__version__}</h3>"
            "<p>基于 PySide6 的桌面图片编辑器。</p>"
            "<p>支持平滑缩放平移、旋转、镜像以及自由和常用比例裁剪；"
            "新功能可以通过 apply_operation 和动作注册表接入。</p>",
        )

    # -- window state ----------------------------------------------------
    def _update_title(self) -> None:
        if self._document.is_empty:
            self.setWindowTitle("Image Edit")
            return
        marker = " *" if self._document.is_modified else ""
        self.setWindowTitle(f"{self._document.display_name}{marker} - Image Edit")

    def _update_document_labels(self) -> None:
        if not self._document.is_empty:
            image = self._document.image
            self._size_label.setText(f"{image.width()} × {image.height()}")

    def _update_action_states(self) -> None:
        has_image = not self._document.is_empty
        for key in (
            "file.save",
            "file.save_as",
            "image.rotate_left",
            "image.rotate_right",
            "image.rotate_180",
            "image.flip_horizontal",
            "image.flip_vertical",
            "image.crop.free",
            *[key for key, _, _ in CROP_RATIOS],
            "view.zoom_in",
            "view.zoom_out",
            "view.actual_size",
            "view.fit",
        ):
            self._actions.action(key).setEnabled(has_image)
        if self._crop_menu_button is not None:
            self._crop_menu_button.setEnabled(has_image)

    def _restore_window_state(self) -> None:
        geometry = self._settings.value("window/geometry", QByteArray())
        if not (isinstance(geometry, QByteArray) and self.restoreGeometry(geometry)):
            self.resize(1100, 720)

        state = self._settings.value("window/state", QByteArray())
        if isinstance(state, QByteArray) and not state.isEmpty():
            self.restoreState(state)

    def _save_window_state(self) -> None:
        self._settings.setValue("window/geometry", self.saveGeometry())
        self._settings.setValue("window/state", self.saveState())
        self._settings.sync()

    def _last_directory(self) -> Path:
        raw = self._settings.value("files/last_directory", "", type=str)
        directory = Path(raw) if raw else Path.home()
        return directory if directory.is_dir() else Path.home()

    def _remember_directory(self, path: Path) -> None:
        self._settings.setValue("files/last_directory", str(path.parent))

    # -- closing and drag/drop -------------------------------------------
    def _confirm_discard(self) -> bool:
        if not self._document.is_modified:
            return True

        answer = QMessageBox.question(
            self,
            "未保存的更改",
            f"“{self._document.display_name}”有未保存的更改，是否保存？",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self.save()
        return answer == QMessageBox.StandardButton.Discard

    def showEvent(self, event) -> None:
        if not self._titlebar_themed:
            self._titlebar_themed = True
            enable_dark_title_bar(self)
        super().showEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._confirm_discard():
            event.ignore()
            return
        self._save_window_state()
        super().closeEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._dropped_path(event) is not None:
            self._canvas.set_drop_active(True)
            event.acceptProposedAction()
        else:
            self._canvas.set_drop_active(False)
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._canvas.set_drop_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._canvas.set_drop_active(False)
        path = self._dropped_path(event)
        if path is None or not self._confirm_discard():
            event.ignore()
            return
        self._load_path_unchecked(path)
        event.acceptProposedAction()

    @staticmethod
    def _dropped_path(event: QDragEnterEvent | QDropEvent) -> Path | None:
        mime = event.mimeData()
        if not mime.hasUrls():
            return None
        for url in mime.urls():
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                if is_supported_image(path):
                    return path
        return None
