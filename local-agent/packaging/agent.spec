# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec: packages scAnnoRare Local Agent as a standalone onedir executable.
# The agent is a bridge/scheduler only — scientific computing dependencies are
# intentionally excluded and must come from the user's locally selected Python environment.
import os
from PyInstaller.utils.hooks import collect_submodules

AGENT_ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
RUNNERS = os.path.join(AGENT_ROOT, "runners")

datas, binaries, hiddenimports = [], [], []

# Collect dynamically loaded submodules for uvicorn / fastapi internals
for pkg in ["uvicorn", "anyio", "starlette"]:
    hiddenimports += collect_submodules(pkg)

# Bundle runner scripts; at runtime these are invoked via the user's selected Python env.
datas += [(os.path.join(RUNNERS, f), "runners")
          for f in os.listdir(RUNNERS) if f.endswith(".py")]

a = Analysis(
    [os.path.join(AGENT_ROOT, "main.py")],
    pathex=[AGENT_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ["app.api.env", "app.api.files", "app.api.tasks", "app.api.envs"],
    excludes=[
        # Scientific computing libs must come from the user's local Python env, not this bundle.
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
    console=True,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=False,
    name="scannorare-agent",
)
