# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：把 scAnnoRare Local Agent 打成独立可执行（onedir）。"""
import os
from PyInstaller.utils.hooks import collect_submodules

AGENT_ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
RUNNERS = os.path.join(AGENT_ROOT, "runners")

datas, binaries, hiddenimports = [], [], []

# uvicorn / fastapi 动态加载的子模块
for pkg in ["uvicorn", "anyio", "starlette"]:
    hiddenimports += collect_submodules(pkg)

# 随包携带 runner 脚本；运行时由用户选择的本地 Python 环境调用。
datas += [(os.path.join(RUNNERS, f), "runners")
          for f in os.listdir(RUNNERS) if f.endswith(".py")]

a = Analysis(
    [os.path.join(AGENT_ROOT, "main.py")],
    pathex=[AGENT_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ["app.api.env", "app.api.files", "app.api.tasks", "app.api.envs"],
    excludes=[
        # Local Agent 只做桥接与调度；科学计算依赖必须来自用户选择的本地 Python 环境。
        "anndata", "celltypist", "h5py", "jinja2", "matplotlib", "numba", "numpy",
        "pandas", "pynndescent", "scanpy", "scipy", "scvi", "scvi-tools",
        "seaborn", "sklearn", "torch", "umap",
        "tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6",
        "IPython", "notebook", "jupyter", "pytest",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="scannorare-agent",
    console=True,        # 先保留控制台便于调试；正式发布可改 False
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=False,
    name="scannorare-agent",
)
