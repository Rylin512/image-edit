# image-edit

这是一个基于 Python 的桌面图片编辑器项目模板，目标是建立一个可持续扩展的图像编辑软件基础架构。

## 项目目标

- 使用 Python + PySide6 构建桌面应用界面
- 适合后续扩展图像编辑功能，如裁剪、缩放、旋转、滤镜、导出等

## 仓库的门禁策略

建议在 GitHub 中对 `main` 分支启用分支保护，配置如下：

1. 打开 `Settings` → `Branches`
2. 创建分支保护规则，作用于 `main`
3. 启用：
   - `Require a pull request before merging`
   - `Require status checks to pass before merging`
   - 选择检查项：`lint`、`test`、`build`（对应 `ci.yml` 中的三个 job）
4. 不启用：
   - `Require approvals`
   - `Require review from Code Owners`

这样可以实现：
- PR 可以创建
- CI 自动运行检查
- 若检查失败，PR 不能合并
- 不要求其他人点 Approve


## 这个仓库包含的内容

当前仓库应包含一个可运行的桌面程序骨架，以及一个 CI 工作流：

- Python 代码结构
- PySide6 桌面窗口
- 文件打开与导出按钮
- Black 格式检查
- Ruff 代码检查
- pytest 测试
- Python 编译检查

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

如果你使用 Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.main
```

## 开发检查

```bash
pip install -r requirements-dev.txt
black --check .
ruff check .
pytest -q
python -m compileall app
```

这些命令与 CI 中的 `lint`、`test`、`build` 三个检查一致。

## 项目结构

```text
.
├── .github/
│   └── workflows/
│       └── ci.yml
├── app/
│   ├── __init__.py
│   └── main.py
├── tests/
│   ├── conftest.py
│   └── test_app.py
├── .gitignore
├── LICENSE
├── README.md
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

`app/main.py` 提供主窗口、打开/导出功能；`tests/` 中的测试默认使用 Qt 的
`offscreen` 平台，无需显示器即可运行。

## CI 工作流说明

仓库中的 GitHub Actions 会在以下场景自动触发：

- 推送到 `main`
- 向 `main` 提交 PR

会执行：

- `black --check .`
- `ruff check .`
- `pytest -q`
- `python -m compileall app`

只有这些检查全部通过，分支才能被认为“可合并”。

## 后续开发路线

建议按照下面顺序推进：

1. 图片打开与显示
2. 画布浏览与缩放
3. 裁剪、旋转、调整大小
4. 色彩、亮度和对比度调节
5. 图层管理
6. 撤销/重做
7. PNG/JPEG/WebP 导出
8. PyInstaller 打包为桌面应用

## 备注

这个项目目前是“基础骨架”，用于搭建开发环境和 CI 门禁，后续可以逐步加入真实的图像编辑功能。由于你希望走“CI 作为唯一门禁”的模式，因此仓库设置需要在 GitHub 页面中完成分支保护规则配置。
