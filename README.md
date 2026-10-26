# image-edit

基于 Python + PySide6 的桌面图片编辑器**基础平台**。

当前版本只做“地基”：文档模型、撤销/重做（最多 20 步）、缩放画布、原子保存、EXIF 方向校正、动作注册表、日志、设置持久化，以及 Windows 一键启动与打包流程。裁剪、滤镜、图层等编辑功能留待后续按统一方式接入，不在本版本中。

## 设计原则

- **易扩展**：`core / ui / utils` 分层。新增一个图像操作通常只需要一个纯函数；菜单、快捷键、撤销栈都是现成的。
- **低开销**：画布基于 `QGraphicsView`，缩放和平移只改图像项的浮点变换，不重采样整张图片；过渡动画也只改变换和透明度，不重建像素。
- **可测试**：核心逻辑与界面解耦，测试使用 Qt 的 `offscreen` 平台，无显示器也能跑。
- **可交付**：`run.bat` 一键启动；PyInstaller 生成免安装便携版；Inno Setup 生成安装包。

## 一键启动（免部署）

双击根目录的 `run.bat`。

- 首次运行会自动创建 `.venv` 并安装依赖（需要本机已有 Python 3.12+，首次会下载 PySide6，耗时几分钟）。
- 之后每次启动只做一次依赖哈希检查，直接拉起应用，不弹控制台窗口。
- 依赖变化时（修改了 `requirements.txt`）会自动重新安装。

开发模式（带控制台、方便看报错）：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python -m app
```

## 架构

```text
.
├── app/
│   ├── __main__.py          # python -m app / PyInstaller 入口
│   ├── main.py              # 启动流程，--smoke-test
│   ├── application.py       # QApplication、日志、异常钩子、主题
│   ├── core/
│   │   ├── document.py      # ImageDocument：图片 + 路径 + 脏标记 + 原子保存/EXIF 方向
│   │   └── commands.py      # QUndoStack 图像操作封装
│   ├── ui/
│   │   ├── main_window.py   # 菜单、工具栏、状态栏、文件读写
│   │   ├── canvas.py        # QGraphicsView 画布：缩放/平移/动画/坐标
│   │   ├── actions.py       # ActionRegistry：声明式动作/菜单注册
│   │   ├── icons.py         # QPainter 绘制的多倍率线性图标
│   │   └── theme.py         # 深色主题、QSS、Windows 深色标题栏
│   ├── utils/
│   │   ├── files.py         # 文件过滤器、保存格式校验与扩展名
│   │   ├── logging.py       # 滚动日志（%LOCALAPPDATA%\Rylin512\ImageEdit\logs）
│   │   └── paths.py         # 数据目录 / PyInstaller 资源路径
│   └── resources/           # icon.png / icon.ico
├── tests/                   # 文档、命令、画布、主窗口测试
├── scripts/
│   ├── launch.py            # run.bat 的引导逻辑
│   └── make_icon.py         # 生成图标（PNG + 多尺寸 ICO）
├── packaging/
│   ├── image_edit.spec      # PyInstaller onedir
│   ├── build.ps1            # 构建便携版 + 冒烟测试 + zip
│   ├── build_installer.ps1  # 构建安装包
│   └── installer.iss        # Inno Setup 脚本
├── run.bat                  # 一键启动
├── requirements*.txt
└── pyproject.toml
```

### 关键对象

| 对象 | 职责 |
| --- | --- |
| `ImageDocument` | 持有 `QImage`、路径、脏标记；原子保存、EXIF 方向校正；`imageChanged/pathChanged/modifiedChanged` 信号 |
| `CanvasView` | 显示图片；滚轮以光标为锚点缓动缩放，左键/中键拖拽平移，打开图片淡入，拖放高亮 |
| `ImageOperationCommand` | 把 `QImage -> QImage` 操作变成可撤销命令，只保留一份“操作前”快照 |
| `ActionRegistry` | 创建/登记 `QAction`，再声明式挂到菜单和工具栏 |
| `MainWindow` | 组装以上对象，负责打开/保存/关闭确认/窗口状态持久化 |

### 界面与动画

- **主题**：Fusion + 深色调色板 + QSS；工具按钮、菜单、状态栏统一圆角和悬停态。Windows 10/11 上同时把原生标题栏切换为深色。
- **图标**：`icons.py` 用 `QPainter` 直接绘制打开/保存/撤销/重做/缩放/适应等线性图标，按 1x/2x/3x 生成，不需要外部图片资源。
- **过渡**：滚轮缩放 90ms、按钮缩放 160ms、打开图片淡入 180ms、拖放提示 150ms，全部使用 `OutCubic` 缓动。
- **平滑缩放**：画布隐藏原生滚动条，改用图像项的浮点变换定位；缩放锚点和高 DPI 下的位移都不受滚动条整像素取整影响。
- **空状态**：没有图片时在画布上绘制图标、标题和操作提示；拖入文件时显示虚线高亮。

动画只改 `QGraphicsPixmapItem` 的变换和透明度，不会在每一帧重新处理 `QImage`。测试和截图可以用 `canvas.finish_animations()` 直接跳到动画终点。

## 扩展指南

### 添加一个图像操作（例如反色）

```python
from PySide6.QtGui import QImage


def invert(image: QImage) -> QImage:
    image.invertPixels()   # 操作拿到的已经是副本
    return image


# 在主窗口里执行：自动入撤销栈，自动刷新画布与标题
window.apply_operation("反色", invert)
```

约定：操作必须是**纯函数且确定性**，输入和输出都是 `QImage`。命令只保存操作前快照，重做时重新计算，这样内存约为两张图而不是三张；撤销栈最多保留 20 步。

### 把操作挂到菜单/工具栏

```python
action = window.actions.create(
    "edit.invert",
    "反色(&I)",
    slot=lambda: window.apply_operation("反色", invert),
    shortcut="Ctrl+I",
    status_tip="对当前图片反色",
)
window.actions.add("edit", "edit.invert")   # 追加到“编辑”菜单
```

新动作的启用/禁用状态需要功能模块自己维护；内置动作的启用逻辑在 `MainWindow._update_action_states()`。

### 添加画布工具（后续）

`CanvasView` 已经把缩放、平移、坐标映射隔离好了。后续工具可以：

- 继承 `CanvasView` 或在其上叠加 `QGraphicsItem`（裁剪框、控制点）；
- 使用 `cursorPositionChanged` 获取图片像素坐标；
- 用 `view_to_image()`、`image_to_view()` 和 `image_rect()` 在视口与图片坐标之间转换；
- 在 `mousePressEvent/mouseMoveEvent` 中实现交互，完成后仍然通过 `apply_operation` 提交修改，从而自动获得撤销能力。

注意：当前左键拖动默认用于平移。接入画笔/选框等工具后，需要在工具激活时关闭左键平移（例如增加 `left_drag_pans` 开关），把左键事件交给工具处理。

### 添加自定义命令

如果操作不是“整图替换”（例如图层增删），直接继承 `QUndoCommand`，把命令 `push` 到 `window.undo_stack` 即可。

## 打包

### 便携版（免安装）

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build.ps1
```

产物：

- `dist\ImageEdit\ImageEdit.exe` —— 双击即用
- `dist\ImageEdit-portable.zip` —— 整个目录压缩，解压后运行

构建脚本会在打包后自动执行 `ImageEdit.exe --smoke-test`，启动 300ms 后退出，用来确认冻结后的 Qt 能正常启动。

### 安装包

先安装 [Inno Setup](https://jrsoftware.org/isinfo.php)（只需一次）：

```powershell
winget install -e --id JRSoftware.InnoSetup
```

然后：

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_installer.ps1
```

产物：`dist\ImageEdit-Setup-0.1.0.exe`。默认按当前用户安装到 `%LOCALAPPDATA%\Programs\Image Edit`，无需管理员权限，带开始菜单快捷方式和可选桌面图标。安装包和 `pyproject.toml` 都从 `app.__version__` 读取版本号，只需修改一处。

> 未签名的 exe 首次运行可能触发 Windows SmartScreen 提示；正式分发需要代码签名证书。

## 开发检查

```bash
pip install -r requirements-dev.txt
black --check .
ruff check .
pytest -q
python -m compileall app scripts tests
```

`black`/`ruff` 版本固定在 `requirements-lint.txt`，与 CI 一致。以上检查对应 CI 中的 `lint`、`test`、`build` 三个 Linux job；Windows 打包由 `package-windows` job 自动完成。`main` 分支建议启用分支保护，把 Linux 检查设为必需（README 末尾有说明）。

## 性能说明

- 画布只用图像项的浮点变换定位，缩放/平移不重建像素；窗口拉伸时只重新计算适配比例。
- 缩放、淡入和拖放动画只更新变换、透明度或重绘覆盖层，不复制图片数据。
- 图片只从 `QImage` 转成 `QPixmap` 一次，随后由 Qt 绘制。
- 鼠标移动只更新状态栏文本，不写日志；日志仅记录启动、打开/保存和异常。
- 撤销命令最多保留 20 步，只保存“操作前”快照，重做时重算；超出后丢弃最旧记录，后续可针对具体操作实现增量命令。
- 图片加载目前是同步的，超大文件会短暂阻塞界面；后续可改为 `QThreadPool` 异步加载。

## 已知限制

- 保存会重新编码图片：JPEG、WebP 为有损格式（JPEG 默认质量 92），EXIF、ICC、XMP 等元数据不会写回。加载时会按 EXIF 方向自动旋转，避免照片横置。
- JPEG 不支持透明通道；交互式保存带透明区域的图片到 JPEG 时会先提示确认。
- 动图（GIF/WebP）只加载第一帧。
- 撤销栈最多保留 20 步；每步保存一张完整“操作前”快照，超大图片连续编辑时内存会随步数增长。

## 后续路线

1. 画布交互工具框架（选择框、画笔、取色）
2. 裁剪、旋转、调整大小
3. 色彩、亮度、对比度调节
4. 图层管理
5. 撤销/重做粒度优化（增量快照）
6. PNG/JPEG/WebP 导出选项（质量、元数据）
7. 最近文件、拖放/粘贴板、异步加载
8. 代码签名与自动发布

## CI 与分支保护

GitHub Actions 在推送到 `main` 或向 `main` 提 PR 时运行四个 job：

- `lint`：`black --check .`、`ruff check .`
- `test`：`pytest -q`
- `build`：`compileall` + `pip install --no-deps .`（校验包元数据）
- `package-windows`：在 Windows 上构建便携版和安装包，冒烟测试后上传产物

启用分支保护：`Settings` → `Rules` → `Rulesets`，对 `main` 启用 `Require a pull request before merging` 和 `Require status checks to pass before merging`，勾选 `lint`、`test`、`build`（`package-windows` 可选）。无需强制 Approve。

## 备注

`--smoke-test` 是内部参数，只用于打包脚本和自动化检查；正常启动不需要它。
