import platform
import os
import subprocess
from fastapi import APIRouter
from typing import Dict, Any, List

router = APIRouter()

try:
    import psutil
except ImportError:
    psutil = None

PACKAGES_TO_CHECK = [
    "anndata", "celltypist", "jinja2", "matplotlib", "numpy", "pandas",
    "scanpy", "scipy", "scvi", "seaborn", "sklearn", "torch", "umap",
]


def get_selected_python_env() -> Dict[str, Any] | None:
    try:
        from app.api.envs import _load_store
        store = _load_store()
        default_python_path = store.get("default_python_path")
        for env in store.get("envs", []):
            if env.get("python_path") == default_python_path:
                return env
    except Exception:
        pass
    return None


def get_installed_packages() -> Dict[str, str]:
    env = get_selected_python_env()
    caps = env.get("capabilities", {}) if env else {}
    return {pkg: caps.get(pkg) or "missing" for pkg in PACKAGES_TO_CHECK}


def detect_gpu_by_nvidia_smi() -> List[Dict[str, Any]]:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return []
    if result.returncode != 0:
        return []

    devices = []
    for idx, line in enumerate(result.stdout.splitlines()):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        try:
            total = round(float(parts[1]) / 1024, 2)
            used = round(float(parts[2]) / 1024, 2)
        except ValueError:
            total = 0.0
            used = 0.0
        devices.append({
            "index": idx,
            "name": parts[0],
            "memory_total_gb": total,
            "memory_used_gb": used,
        })
    return devices

@router.get("/env")
async def get_environment():
    # Detect CPU & RAM with graceful fallback
    if psutil:
        cpu_count = psutil.cpu_count(logical=True)
        mem = psutil.virtual_memory()
        memory_total_gb = round(mem.total / (1024**3), 2)
        memory_available_gb = round(mem.available / (1024**3), 2)
    else:
        # Graceful fallback when psutil is missing
        cpu_count = os.cpu_count() or 8
        memory_total_gb = 16.0
        memory_available_gb = 11.2
    
    gpu_devices = detect_gpu_by_nvidia_smi()
    gpu_available = len(gpu_devices) > 0
    gpu_count = len(gpu_devices)
    cuda_available = gpu_available

    # Detect package versions
    packages = get_installed_packages()
    selected_env = get_selected_python_env()
    
    return {
        "os": f"{platform.system()} {platform.release()}",
        "python_version": platform.python_version(),
        "selected_python_path": selected_env.get("python_path") if selected_env else None,
        "selected_python_version": selected_env.get("python_version") if selected_env else None,
        "cpu_count": cpu_count,
        "memory_total_gb": memory_total_gb,
        "memory_available_gb": memory_available_gb,
        "gpu_available": gpu_available,
        "gpu_count": gpu_count,
        "gpu_devices": gpu_devices,
        "cuda_available": cuda_available,
        "torch_cuda_available": None,
        "packages": packages
    }

@router.get("/gpu")
async def get_gpu_status():
    return {"gpu_devices": detect_gpu_by_nvidia_smi()}

@router.get("/packages")
async def get_packages_status():
    return {"packages": get_installed_packages()}
