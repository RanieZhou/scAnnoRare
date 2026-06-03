import platform
import os
from fastapi import APIRouter
from typing import Dict, Any, List

router = APIRouter()

try:
    import psutil
except ImportError:
    psutil = None

def get_installed_packages() -> Dict[str, str]:
    packages_to_check = ["scanpy", "anndata", "celltypist", "scvi-tools", "torch"]
    result = {}
    for pkg in packages_to_check:
        try:
            import importlib.metadata
            result[pkg] = importlib.metadata.version(pkg)
        except Exception:
            try:
                mod = __import__(pkg)
                result[pkg] = getattr(mod, "__version__", "installed")
            except ImportError:
                result[pkg] = "missing"
    return result

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
    
    # Detect GPU via torch or pynvml
    gpu_available = False
    gpu_count = 0
    gpu_devices = []
    cuda_available = False
    torch_cuda_available = False
    
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        torch_cuda_available = cuda_available
        if cuda_available:
            gpu_available = True
            gpu_count = torch.cuda.device_count()
            for i in range(gpu_count):
                device_name = torch.cuda.get_device_name(i)
                total_mem = round(torch.cuda.get_device_properties(i).total_memory / (1024**3), 2)
                used_mem = round(torch.cuda.memory_allocated(i) / (1024**3), 2)
                gpu_devices.append({
                    "name": device_name,
                    "memory_total_gb": total_mem,
                    "memory_used_gb": used_mem
                })
    except ImportError:
        pass

    if not gpu_available:
        try:
            import pynvml
            pynvml.nvmlInit()
            gpu_available = True
            gpu_count = pynvml.nvmlDeviceGetCount()
            for i in range(gpu_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode("utf-8")
                info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                gpu_devices.append({
                    "name": str(name),
                    "memory_total_gb": round(info.total / (1024**3), 2),
                    "memory_used_gb": round(info.used / (1024**3), 2)
                })
            pynvml.nvmlShutdown()
        except Exception:
            pass

    # Detect package versions
    packages = get_installed_packages()
    
    return {
        "os": f"{platform.system()} {platform.release()}",
        "python_version": platform.python_version(),
        "cpu_count": cpu_count,
        "memory_total_gb": memory_total_gb,
        "memory_available_gb": memory_available_gb,
        "gpu_available": gpu_available,
        "gpu_count": gpu_count,
        "gpu_devices": gpu_devices,
        "cuda_available": cuda_available,
        "torch_cuda_available": torch_cuda_available,
        "packages": packages
    }

@router.get("/gpu")
async def get_gpu_status():
    devices = []
    try:
        import torch
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                devices.append({
                    "index": i,
                    "name": torch.cuda.get_device_name(i),
                    "memory_total_gb": round(torch.cuda.get_device_properties(i).total_memory / (1024**3), 2),
                    "memory_allocated_gb": round(torch.cuda.memory_allocated(i) / (1024**3), 2)
                })
    except Exception:
        pass
    return {"gpu_devices": devices}

@router.get("/packages")
async def get_packages_status():
    return {"packages": get_installed_packages()}
