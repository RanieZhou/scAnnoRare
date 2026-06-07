import sys
import os

import uuid
import time
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Initialize logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("local-agent")

app = FastAPI(title="scAnnoRare Local Agent", version="1.0.0")

# Set up CORS and Private Network Access (PNA) middleware
@app.middleware("http")
async def add_cors_and_pna_headers(request: Request, call_next):
    # Handle preflight OPTIONS requests directly to support PNA
    if request.method == "OPTIONS":
        response = Response()
        response.headers["Access-Control-Allow-Origin"] = request.headers.get("origin", "*")
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-scAnnoRare-Origin"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        if request.headers.get("Access-Control-Request-Private-Network") == "true":
            response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response

    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = request.headers.get("origin", "*")
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

# Security store for pairing codes and session tokens
class SecurityStore:
    def __init__(self):
        self.pairing_code: Optional[str] = None
        self.pairing_code_expiry: float = 0.0
        self.failed_attempts: int = 0
        self.session_token: Optional[str] = None
        self.web_origin: Optional[str] = None

security_store = SecurityStore()

# Helper function to check session token
async def verify_token(authorization: Optional[str] = Header(None), x_scannorare_origin: Optional[str] = Header(None)):
    if not security_store.session_token:
        raise HTTPException(status_code=401, detail="Agent is not paired yet.")
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")
    
    token = authorization.split(" ")[1]
    if token != security_store.session_token:
        raise HTTPException(status_code=401, detail="Invalid session token.")
    
    # Optional: origin check
    if x_scannorare_origin and security_store.web_origin and x_scannorare_origin != security_store.web_origin:
        logger.warning(f"Origin mismatch: {x_scannorare_origin} vs {security_store.web_origin}")
        
    return token

class PairRequest(BaseModel):
    pairing_code: str
    origin: str

class PairResponse(BaseModel):
    success: bool
    session_token: Optional[str] = None
    message: str

# 16.4 Unpaired API whitelist: GET /api/v1/local/health, POST /api/v1/local/pair
@app.get("/api/v1/local/health")
async def health_check():
    return {
        "status": "healthy",
        "paired": security_store.session_token is not None,
        "timestamp": time.time()
    }

@app.post("/api/v1/local/pair", response_model=PairResponse)
async def pair_agent(payload: PairRequest):
    if security_store.session_token is not None:
        return PairResponse(success=True, session_token=security_store.session_token, message="Already paired.")

    if not security_store.pairing_code:
        raise HTTPException(status_code=400, detail="No pairing code has been generated. Please generate it on desktop first.")

    if time.time() > security_store.pairing_code_expiry:
        security_store.pairing_code = None
        raise HTTPException(status_code=400, detail="Pairing code has expired.")

    if security_store.failed_attempts >= 5:
        raise HTTPException(status_code=400, detail="Too many failed pairing attempts. Please regenerate pairing code.")

    if payload.pairing_code != security_store.pairing_code:
        security_store.failed_attempts += 1
        raise HTTPException(status_code=400, detail=f"Invalid pairing code. Remaining attempts: {5 - security_store.failed_attempts}")

    # Validation successful, generate session token
    security_store.session_token = str(uuid.uuid4()).replace("-", "")
    security_store.web_origin = payload.origin
    security_store.pairing_code = None  # One-time use
    logger.info(f"Local Agent successfully paired with origin: {payload.origin}")
    
    return PairResponse(
        success=True,
        session_token=security_store.session_token,
        message="Successfully paired with Web Platform."
    )

@app.post("/api/v1/local/unpair", dependencies=[Depends(verify_token)])
async def unpair_agent():
    security_store.session_token = None
    security_store.web_origin = None
    security_store.failed_attempts = 0
    logger.info("Local Agent unpaired successfully.")
    return {"success": True, "message": "Successfully unpaired."}

# Include environment, files and tasks routers below dynamically or implement them directly.
# For simplicity, robustness, and speed, we will implement the routes directly or import them from modules.
# Let's import the routers we're going to create.
try:
    from app.api.env import router as env_router
    from app.api.files import router as files_router
    from app.api.tasks import router as tasks_router
    from app.api.envs import router as envs_router
    app.include_router(env_router, prefix="/api/v1/local", dependencies=[Depends(verify_token)])
    app.include_router(files_router, prefix="/api/v1/local", dependencies=[Depends(verify_token)])
    app.include_router(tasks_router, prefix="/api/v1/local", dependencies=[Depends(verify_token)])
    app.include_router(envs_router, prefix="/api/v1/local", dependencies=[Depends(verify_token)])
except Exception as e:
    logger.error(f"Failed to load sub-routers: {e}")

# Desktop client utility endpoint to generate pairing code
@app.post("/api/v1/local/admin/generate-pairing-code")
async def generate_pairing_code():
    import random
    import string
    # Generate 6-8 digits/uppercase letters
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    security_store.pairing_code = code
    security_store.pairing_code_expiry = time.time() + 300.0  # 5 minutes validity
    security_store.failed_attempts = 0
    security_store.session_token = None  # Reset session token for new pairing session
    
    logger.info(f"Generated new admin pairing code: {code}")
    return {
        "success": True,
        "pairing_code": code,
        "expires_in": 300
    }

@app.get("/api/v1/local/admin/hardware")
async def admin_hardware_info():
    """Returns local hardware info without authentication (desktop shell use only)."""
    import platform
    gpu_devices = []
    try:
        from app.api.env import detect_gpu_by_nvidia_smi
        gpu_devices = detect_gpu_by_nvidia_smi()
    except Exception:
        pass
    try:
        import psutil
        cpu_count = psutil.cpu_count(logical=True)
        mem = psutil.virtual_memory()
        memory_gb = round(mem.total / (1024 ** 3), 1)
    except Exception:
        cpu_count = os.cpu_count() or 0
        memory_gb = 0.0
    return {
        "cpu": {
            "name": platform.processor() or platform.machine(),
            "logical_cores": cpu_count,
            "architecture": platform.machine(),
        },
        "memory_gb": memory_gb,
        "gpu_devices": gpu_devices,
        "platform": platform.system(),
    }


if __name__ == "__main__":
    import uvicorn
    if getattr(sys, "frozen", False):
        # Packaged: pass the app object directly; reload/string-import don't work frozen.
        uvicorn.run(app, host="127.0.0.1", port=17890)
    else:
        uvicorn.run("main:app", host="127.0.0.1", port=17890, reload=True)
