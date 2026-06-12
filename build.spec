# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 — 高考语文刷题助手 (one-folder 模式)
生成: pyinstaller build.spec
输出: dist/GaokaoAgent/
"""

import os
import sys
from pathlib import Path

BASE = Path(".").resolve()

# ---- 数据文件 ----
datas = [
    ("config/llm.yaml", "config"),
    ("config/beijing_gaokao.yaml", "config"),
    (".env.example", "."),
]

# PaddleOCR 模型
paddle_dir = Path(r"C:\paddleocr_models\whl")
if paddle_dir.exists():
    for root, dirs, files in os.walk(paddle_dir):
        for f in files:
            src = Path(root) / f
            rel = src.relative_to(paddle_dir.parent)
            dst = str(rel.parent).replace("\\", "/")
            datas.append((str(src), dst))
    print(f"[build] PaddleOCR models: {paddle_dir}")
else:
    print("[build] WARNING: PaddleOCR models not found")

# ---- 隐藏导入 ----
hiddenimports = [
    "paddleocr", "paddle", "paddleocr.tools.infer",
    "paddleocr.tools.infer.predict_system",
    "paddleocr.tools.infer.predict_det",
    "paddleocr.tools.infer.predict_rec",
    "paddleocr.tools.infer.predict_cls",
    "paddleocr.tools.infer.utility",
    "cv2", "PIL", "numpy", "yaml", "jinja2", "Jinja2", "markdown",
    "weasyprint", "weasyprint.text", "weasyprint.html",
    "sqlite3", "anthropic", "openai", "dotenv",
    "gradio", "gradio._simple_templates", "gradio.components",
    "gradio.blocks", "gradio.layouts", "gradio.themes",
    "uvicorn", "fastapi", "starlette",
    "pydantic", "pydantic_core",
    "paddle.base", "paddle.inference",
    "json", "http", "email", "html", "xml",
    "collections.abc", "copy", "uuid", "queue",
    "concurrent.futures", "multiprocessing",
    "PIL._imaging", "PIL._imagingft",
]

excludes = [
    "tkinter", "unittest", "test", "pydoc",
    "matplotlib", "notebook", "jupyter", "ipython",
    "scipy", "pandas", "IPython",
]

a = Analysis(
    ["launcher.py"],
    pathex=[str(BASE), str(BASE / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="GaokaoAgent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,
)

# one-folder: 所有依赖放在 _internal/ 目录
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="GaokaoAgent",
)
