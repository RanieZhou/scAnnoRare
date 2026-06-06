# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：把 scAnnoRare Local Agent 打成独立可执行（onedir）。"""
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

AGENT_ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
RUNNERS = os.path.join(AGENT_ROOT, "runners")

datas, binaries, hiddenimports = [], [], []

# 收全运行时真正需要的科学计算库（子模块 + 数据文件）
# scanpy/celltypist/umap 为 V1.1 内置方法与 UMAP 可视化所需
for pkg in ["sklearn", "scipy", "matplotlib", "anndata", "seaborn",
            "pandas", "numpy", "h5py", "jinja2",
            "scanpy", "celltypist", "umap", "numba", "llvmlite", "pynndescent"]:
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hiddenimports += h
    except Exception:
        pass

# uvicorn / fastapi 动态加载的子模块
for pkg in ["uvicorn", "anyio", "starlette"]:
    hiddenimports += collect_submodules(pkg)

# 随包携带 runner 脚本（frozen 时由 --run-script 调用）
datas += [(os.path.join(RUNNERS, f), "runners")
          for f in os.listdir(RUNNERS) if f.endswith(".py")]

a = Analysis(
    [os.path.join(AGENT_ROOT, "main.py")],
    pathex=[AGENT_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ["app.api.env", "app.api.files", "app.api.tasks"],
    excludes=[
        # 运行时不需要的重依赖（注意：V1.1 起 scanpy/numba/llvmlite 已改为包含）
        "scvi", "scvi-tools", "torch",
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
