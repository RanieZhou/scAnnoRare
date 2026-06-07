"""
envs.py — Python 环境管理 API
检测用户本地的 conda / pyenv / system Python 环境，
并探测每个环境中安装的科学计算库（scvi-tools, celltypist 等），
供外部方法调用时选择执行环境。
"""
import os
import sys
import glob
import json
import uuid
import time
import shutil
import logging
import subprocess
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

logger = logging.getLogger("local-agent.envs")
router = APIRouter()

# ── 存储路径 ────────────────────────────────────────────────────────────────────
def _workspace_dir() -> str:
    home = os.path.expanduser("~")
    if sys.platform == "darwin":
        base = os.path.join(home, "Library", "Application Support", "scAnnoRare")
    elif sys.platform.startswith("win"):
        base = os.path.join(os.environ.get("APPDATA", home), "scAnnoRare")
    else:
        base = os.path.join(
            os.environ.get("XDG_DATA_HOME", os.path.join(home, ".local", "share")),
            "scAnnoRare"
        )
    return os.path.join(base, "workspace")

_ENVS_FILE = os.path.join(_workspace_dir(), "python_envs.json")
os.makedirs(os.path.dirname(_ENVS_FILE), exist_ok=True)

def _load_store() -> Dict:
    if os.path.exists(_ENVS_FILE):
        try:
            with open(_ENVS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"envs": [], "default_python_path": None, "last_scan": None}

def _save_store(store: Dict):
    os.makedirs(os.path.dirname(_ENVS_FILE), exist_ok=True)
    with open(_ENVS_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)

# ── 探测脚本（在子进程中执行） ──────────────────────────────────────────────────
# 关键：使用 importlib 元数据探测包是否存在及版本，绝不真正 import 重型库。
# 真正 import torch / scvi / scanpy 在 Windows 上会派生子进程做硬件检测，
# 这些子进程持有管道句柄，导致 subprocess 即使超时也无法回收、永久阻塞，
# 同时 import 本身可能耗时数十秒触发超时，使整个扫描卡死或"找不到任何环境"。
_PROBE_CODE = r"""
import json, sys
from importlib.util import find_spec
try:
    from importlib.metadata import version
except Exception:  # Python < 3.8 fallback
    from importlib_metadata import version

# import 名 -> 发行包名（用于读取版本号）
DIST = {'sklearn': 'scikit-learn', 'umap': 'umap-learn', 'scvi': 'scvi-tools'}
PKGS = ['anndata', 'celltypist', 'jinja2', 'matplotlib', 'numpy', 'pandas',
        'scanpy', 'scipy', 'scvi', 'seaborn', 'sklearn', 'torch', 'umap']

caps = {}
for p in PKGS:
    try:
        spec = find_spec(p)   # 仅定位模块，不执行 import，毫秒级返回
    except Exception:
        spec = None
    if spec is None:
        caps[p] = None
        continue
    try:
        caps[p] = version(DIST.get(p, p))
    except Exception:
        caps[p] = 'installed'

print(json.dumps({'python_version': sys.version.split()[0], 'capabilities': caps}))
"""

def _probe_python(python_path: str, timeout: int = 15) -> Optional[Dict]:
    """在指定 Python 中运行探测脚本，返回版本+能力信息。超时或失败返回 None。

    探测脚本只用 importlib 读取元数据（不 import 重型库），通常 1 秒内返回；
    timeout 仅用于防御性兜底（损坏的解释器、网络盘卡顿等）。
    """
    kw: Dict[str, Any] = {}
    if sys.platform.startswith("win"):
        # 抑制黑色控制台窗口（CREATE_NO_WINDOW）
        kw["creationflags"] = 0x08000000
    try:
        result = subprocess.run(
            [python_path, "-I", "-c", _PROBE_CODE],
            capture_output=True, text=True, timeout=timeout,
            stdin=subprocess.DEVNULL, **kw,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
        logger.debug(f"Probe non-zero/empty for {python_path}: rc={result.returncode} err={result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        logger.warning(f"Probe timed out after {timeout}s: {python_path}")
    except Exception as e:
        logger.debug(f"Probe failed {python_path}: {e}")
    return None

def _py_exe(env_root: str) -> str:
    if sys.platform.startswith("win"):
        return os.path.join(env_root, "python.exe")
    return os.path.join(env_root, "bin", "python3")

# ── 扫描各来源 ─────────────────────────────────────────────────────────────────
def _scan_conda() -> List[tuple]:
    """返回 [(python_path, source, display_name), ...]"""
    results = []
    home = os.path.expanduser("~")

    # 读取 ~/.conda/environments.txt（包含 base 环境）
    env_txt = os.path.join(home, ".conda", "environments.txt")
    known_paths: set = set()
    if os.path.exists(env_txt):
        for line in open(env_txt):
            env_root = line.strip()
            if env_root and os.path.isdir(env_root):
                exe = _py_exe(env_root)
                if os.path.isfile(exe) and exe not in known_paths:
                    known_paths.add(exe)
                    name = os.path.basename(env_root) or "base"
                    results.append((exe, "conda", f"{name} (conda)"))

    # 扫描常见 conda 安装目录下的 envs/
    if sys.platform.startswith("win"):
        profile = os.environ.get("USERPROFILE", home)
        search_roots = [
            os.path.join(profile, "Anaconda3"),
            os.path.join(profile, "miniconda3"),
            os.path.join(os.environ.get("PROGRAMDATA", ""), "Anaconda3"),
        ]
    else:
        search_roots = [
            os.path.join(home, "anaconda3"),
            os.path.join(home, "miniconda3"),
            os.path.join(home, "opt", "anaconda3"),
            os.path.join(home, "opt", "miniconda3"),
            "/opt/anaconda3", "/opt/miniconda3",
        ]

    for root in search_roots:
        # base env
        base_exe = _py_exe(root)
        if os.path.isfile(base_exe) and base_exe not in known_paths:
            known_paths.add(base_exe)
            results.append((base_exe, "conda", "base (conda)"))
        # child envs
        envs_dir = os.path.join(root, "envs")
        if os.path.isdir(envs_dir):
            for env_name in os.listdir(envs_dir):
                exe = _py_exe(os.path.join(envs_dir, env_name))
                if os.path.isfile(exe) and exe not in known_paths:
                    known_paths.add(exe)
                    results.append((exe, "conda", f"{env_name} (conda)"))

    return results

def _scan_pyenv() -> List[tuple]:
    results = []
    versions_dir = os.path.join(os.path.expanduser("~"), ".pyenv", "versions")
    if not os.path.isdir(versions_dir):
        return results
    for ver in os.listdir(versions_dir):
        exe = os.path.join(versions_dir, ver, "bin", "python3")
        if os.path.isfile(exe):
            results.append((exe, "pyenv", f"pyenv {ver}"))
    return results

def _scan_system() -> List[tuple]:
    results = []
    if sys.platform.startswith("win"):
        local_app = os.environ.get("LOCALAPPDATA", "")
        candidates = glob.glob(os.path.join(local_app, "Programs", "Python", "Python3*", "python.exe"))
        candidates += glob.glob(r"C:\Python3*\python.exe")
    else:
        candidates = ["/usr/bin/python3", "/usr/local/bin/python3", "/opt/homebrew/bin/python3"]
        candidates += glob.glob("/opt/homebrew/bin/python3.*")
        candidates += glob.glob("/usr/local/bin/python3.*")

    for exe_name in ["python", "python3"]:
        found = shutil.which(exe_name)
        if found:
            candidates.append(found)

    seen = set()
    for exe in candidates:
        if os.path.isfile(exe) and exe not in seen:
            seen.add(exe)
            results.append((exe, "system", f"System ({exe})"))
    return results

def _full_scan() -> List[Dict]:
    """扫描所有来源并探测能力，返回环境列表。

    探测并行执行，使总耗时受限于最慢的单个环境，而非所有环境之和，
    避免在拥有大量解释器时长时间卡顿。
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    all_paths: List[tuple] = []
    all_paths += _scan_conda()
    all_paths += _scan_pyenv()
    all_paths += _scan_system()

    # 去重，保留首次出现的来源/名称
    seen = set()
    unique_paths: List[tuple] = []
    for python_path, source, name in all_paths:
        if python_path in seen:
            continue
        seen.add(python_path)
        unique_paths.append((python_path, source, name))

    logger.info(f"Probing {len(unique_paths)} Python interpreter(s) ...")

    envs: List[Dict] = []
    if not unique_paths:
        return envs

    max_workers = min(8, len(unique_paths))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map = {
            pool.submit(_probe_python, python_path): (python_path, source, name)
            for python_path, source, name in unique_paths
        }
        for future in as_completed(future_map):
            python_path, source, name = future_map[future]
            try:
                probe = future.result()
            except Exception as e:
                logger.debug(f"Probe future error for {python_path}: {e}")
                probe = None
            if probe is None:
                continue
            envs.append({
                "id": uuid.uuid4().hex[:8],
                "name": name,
                "python_path": python_path,
                "source": source,
                "python_version": probe.get("python_version", "?"),
                "capabilities": probe.get("capabilities", {}),
                "probed_at": time.time(),
            })

    logger.info(f"Scan complete: {len(envs)} usable environment(s) found.")
    return envs

# ── 扫描状态（用于进度反馈） ───────────────────────────────────────────────────
_scan_state: Dict = {"running": False, "last_error": None}

def _run_scan_bg():
    _scan_state["running"] = True
    _scan_state["last_error"] = None
    try:
        envs = _full_scan()
        store = _load_store()
        store["envs"] = envs
        store["last_scan"] = time.time()
        _save_store(store)
    except Exception as e:
        logger.error(f"Environment scan failed: {e}")
        _scan_state["last_error"] = str(e)
    finally:
        _scan_state["running"] = False

# ── Schemas ────────────────────────────────────────────────────────────────────
class ProbeRequest(BaseModel):
    python_path: str

class SetDefaultRequest(BaseModel):
    python_path: Optional[str] = None   # None → 清除默认

# ── Endpoints ──────────────────────────────────────────────────────────────────
@router.get("/python-envs")
async def list_python_envs():
    """返回已探测的 Python 环境列表及当前默认环境。"""
    store = _load_store()
    return {
        "envs": store["envs"],
        "default_python_path": store.get("default_python_path"),
        "last_scan": store.get("last_scan"),
        "scanning": _scan_state["running"],
    }

@router.post("/python-envs/detect")
async def detect_python_envs(background_tasks: BackgroundTasks):
    """触发后台重新扫描所有 Python 环境（异步，用 GET /python-envs 轮询结果）。"""
    if _scan_state["running"]:
        return {"success": False, "message": "扫描已在进行中，请稍候"}
    background_tasks.add_task(_run_scan_bg)
    return {"success": True, "message": "环境扫描已启动，约需 10–30 秒"}

@router.post("/python-envs/probe")
async def probe_env(payload: ProbeRequest):
    """即时探测指定 Python 可执行路径，返回版本和能力信息，并保存到列表。"""
    python_path = payload.python_path
    if not os.path.isfile(python_path):
        raise HTTPException(status_code=400, detail=f"文件不存在：{python_path}")
    probe = _probe_python(python_path, timeout=20)
    if probe is None:
        raise HTTPException(status_code=422, detail="探测失败：无法执行该 Python 或输出解析错误")

    store = _load_store()
    existing = next((e for e in store["envs"] if e["python_path"] == python_path), None)
    if existing:
        existing.update({
            "python_version": probe["python_version"],
            "capabilities": probe["capabilities"],
            "probed_at": time.time(),
        })
    else:
        store["envs"].append({
            "id": uuid.uuid4().hex[:8],
            "name": f"Custom ({python_path})",
            "python_path": python_path,
            "source": "custom",
            "python_version": probe["python_version"],
            "capabilities": probe["capabilities"],
            "probed_at": time.time(),
        })
    _save_store(store)
    return {"success": True, "python_version": probe["python_version"], "capabilities": probe["capabilities"]}

@router.put("/python-envs/default")
async def set_default_env(payload: SetDefaultRequest):
    """设置（或清除）默认外部执行环境。"""
    store = _load_store()
    if payload.python_path is not None:
        match = next((e for e in store["envs"] if e["python_path"] == payload.python_path), None)
        if match is None:
            raise HTTPException(status_code=404, detail="该环境不在已知列表中，请先探测")
    store["default_python_path"] = payload.python_path
    _save_store(store)
    return {"success": True, "default_python_path": payload.python_path}

@router.delete("/python-envs/{env_id}")
async def remove_env(env_id: str):
    """从列表中移除一个环境记录（不影响实际安装）。"""
    store = _load_store()
    before = len(store["envs"])
    store["envs"] = [e for e in store["envs"] if e["id"] != env_id]
    if len(store["envs"]) == before:
        raise HTTPException(status_code=404, detail="环境 ID 不存在")
    if store.get("default_python_path") and not any(
        e["python_path"] == store["default_python_path"] for e in store["envs"]
    ):
        store["default_python_path"] = None
    _save_store(store)
    return {"success": True}
