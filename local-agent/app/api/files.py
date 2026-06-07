import os
import sys
import json
import logging
import subprocess
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

logger = logging.getLogger("local-agent.files")
router = APIRouter()

# 文件浏览：允许浏览的扩展名（数据集 / 预测结果）
BROWSE_EXTS = (".h5ad", ".csv")


def _workspace_dir() -> str:
    home = os.path.expanduser("~")
    if sys.platform == "darwin":
        base = os.path.join(home, "Library", "Application Support", "scAnnoRare")
    elif sys.platform.startswith("win"):
        base = os.path.join(os.environ.get("APPDATA", home), "scAnnoRare")
    else:
        base = os.path.join(
            os.environ.get("XDG_DATA_HOME", os.path.join(home, ".local", "share")),
            "scAnnoRare",
        )
    return os.path.join(base, "workspace")


_DRIVES_ROOT = "__drives__"  # Windows 虚拟根，用于列出所有驱动器


def _list_windows_drives() -> List[Dict[str, Any]]:
    drives = []
    if sys.platform.startswith("win"):
        import string
        import ctypes
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drives.append({"name": f"{letter}:", "path": f"{letter}:\\"})
            bitmask >>= 1
    return drives


@router.get("/files/open-dialog")
async def open_file_dialog(exts: Optional[str] = None):
    """调用系统原生文件选择对话框，返回用户选中的文件路径。"""
    import asyncio

    ext_list = [e.strip().lower() for e in exts.split(",")] if exts else list(BROWSE_EXTS)
    filetypes = [(f"{e.lstrip('.').upper()} 文件", f"*{e}") for e in ext_list]
    filetypes.append(("所有文件", "*.*"))

    def _open_dialog():
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(title="选择文件", filetypes=filetypes)
        root.destroy()
        return path

    loop = asyncio.get_event_loop()
    filepath = await loop.run_in_executor(None, _open_dialog)

    if not filepath:
        return {"path": None, "cancelled": True}
    return {"path": os.path.normpath(filepath), "cancelled": False}


@router.get("/files/browse")
async def browse_dir(path: Optional[str] = None, exts: Optional[str] = None):
    """列出目录内容（仅返回子目录 + 指定扩展名文件），供前端文件选择弹窗使用。

    path: 目标目录绝对路径，缺省为用户主目录。传 "__drives__" 返回 Windows 所有驱动器。
    exts: 逗号分隔的扩展名过滤（如 ".h5ad" 或 ".csv"），缺省为 .h5ad,.csv。
    """
    # Windows 虚拟根：列出所有驱动器
    if path == _DRIVES_ROOT:
        return {
            "current": _DRIVES_ROOT,
            "parent": None,
            "home": os.path.expanduser("~"),
            "dirs": _list_windows_drives(),
            "files": [],
        }

    base = path or os.path.expanduser("~")
    base = os.path.abspath(os.path.expanduser(base))
    if not os.path.isdir(base):
        raise HTTPException(status_code=400, detail=f"目录不存在：{base}")

    allow = tuple(e.strip().lower() for e in exts.split(",")) if exts else BROWSE_EXTS

    dirs: List[Dict[str, Any]] = []
    files: List[Dict[str, Any]] = []
    try:
        for name in sorted(os.listdir(base), key=str.lower):
            if name.startswith("."):
                continue  # 跳过隐藏项
            full = os.path.join(base, name)
            try:
                if os.path.isdir(full):
                    dirs.append({"name": name, "path": full})
                elif name.lower().endswith(allow):
                    files.append({"name": name, "path": full,
                                  "size": os.path.getsize(full)})
            except OSError:
                continue
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"无权限读取目录：{base}")

    # 计算父目录；Windows 驱动器根（如 C:\）的父目录设为虚拟磁盘根
    raw_parent = os.path.dirname(base.rstrip(os.sep))
    if sys.platform.startswith("win") and raw_parent == base:
        # 已在驱动器根，上级指向虚拟磁盘列表
        parent_path: Optional[str] = _DRIVES_ROOT
    elif raw_parent and raw_parent != base:
        parent_path = raw_parent
    else:
        parent_path = None

    return {
        "current": base,
        "parent": parent_path,
        "home": os.path.expanduser("~"),
        "dirs": dirs,
        "files": files,
    }


# Schema definitions
class FileSelectRequest(BaseModel):
    filepath: str

class DatasetRegisterRequest(BaseModel):
    filepath: str
    dataset_name: str
    label_col: str
    batch_col: Optional[str] = None
    rare_threshold: Optional[float] = 0.05  # default 5%

# Helper to check whether the path points to an h5ad dataset candidate.
def is_h5ad_file(path: str) -> bool:
    if not os.path.exists(path):
        return False
    if not path.endswith(".h5ad"):
        return False
    return True


def _run_dataset_inspector(mode: str, *args) -> Dict[str, Any]:
    from app.api.tasks import RUNNERS_DIR, _POPEN_KW, _get_external_python

    tmp_dir = os.path.join(_workspace_dir(), "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    output_json = os.path.join(tmp_dir, f"inspect_{uuid.uuid4().hex[:8]}.json")
    runner = os.path.join(RUNNERS_DIR, "inspect_dataset.py")
    cmd = [_get_external_python(), runner, mode, output_json, *map(str, args)]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            **_POPEN_KW,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"无法调用本地 Python 环境：{e}")

    result: Dict[str, Any] = {}
    if os.path.exists(output_json):
        try:
            with open(output_json, "r", encoding="utf-8") as f:
                result = json.load(f)
        except Exception:
            result = {}

    if proc.returncode != 0 or not result.get("success"):
        detail = result.get("error") or proc.stderr.strip() or "本地 Python 环境解析数据集失败。"
        raise HTTPException(status_code=500, detail=detail)
    return result

@router.post("/files/select")
async def select_file(payload: FileSelectRequest):
    """
    Validate the file path and inspect h5ad metadata via the selected local Python.
    """
    path = payload.filepath
    if not os.path.exists(path):
        raise HTTPException(status_code=400, detail="File path does not exist.")
    if not is_h5ad_file(path):
        raise HTTPException(status_code=400, detail="File is not a valid .h5ad file.")
    
    return _run_dataset_inspector("select", path)

@router.post("/files/register-dataset")
async def register_dataset(payload: DatasetRegisterRequest):
    """
    Inspect label/batch distribution and find rare candidates.
    """
    path = payload.filepath
    if not is_h5ad_file(path):
        raise HTTPException(status_code=400, detail="Invalid .h5ad file path.")
    
    try:
        summary = _run_dataset_inspector(
            "register",
            path,
            payload.dataset_name,
            payload.label_col,
            payload.batch_col or "None",
            payload.rare_threshold,
        )
        # Save registration info locally in a JSON file registry (19.4 Local workspace)
        workspace_dir = _workspace_dir()
        os.makedirs(workspace_dir, exist_ok=True)
        datasets_dir = os.path.join(workspace_dir, "datasets")
        os.makedirs(datasets_dir, exist_ok=True)
        
        registry_path = os.path.join(datasets_dir, "dataset_registry.json")
        registry = {}
        if os.path.exists(registry_path):
            try:
                with open(registry_path, "r", encoding="utf-8") as f:
                    registry = json.load(f)
            except Exception:
                pass
                
        registry[payload.dataset_name] = summary
        
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=4, ensure_ascii=False)

        return {
            "success": True,
            "dataset_name": payload.dataset_name,
            "summary": registry[payload.dataset_name]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to register dataset: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze dataset obs: {str(e)}")
