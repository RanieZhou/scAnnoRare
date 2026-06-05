import os
import sys
import json
import uuid
import time
import sqlite3
import logging
import subprocess
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from fastapi.responses import FileResponse

logger = logging.getLogger("local-agent.tasks")
router = APIRouter()


def runner_cmd(script_path, *args):
    """Build the command to run a runner script.

    In a normal Python environment we invoke the runner with the current
    interpreter (sys.executable). When packaged with PyInstaller (sys.frozen),
    there is no external ``python``; the frozen executable re-invokes itself
    via the ``--run-script`` entry handler defined in main.py.
    """
    if getattr(sys, "frozen", False):
        return [sys.executable, "--run-script", script_path, *map(str, args)]
    return [sys.executable, script_path, *map(str, args)]


# Windows：spawn 子进程时抑制黑色控制台窗口闪现（CREATE_NO_WINDOW）。
_POPEN_KW = {"creationflags": 0x08000000} if sys.platform.startswith("win") else {}

def _user_data_dir() -> str:
    """跨平台用户可写数据目录（打包后 app bundle 内只读，workspace 必须落在此处）。"""
    home = os.path.expanduser("~")
    if sys.platform == "darwin":
        base = os.path.join(home, "Library", "Application Support", "scAnnoRare")
    elif sys.platform.startswith("win"):
        base = os.path.join(os.environ.get("APPDATA", home), "scAnnoRare")
    else:
        base = os.path.join(os.environ.get("XDG_DATA_HOME", os.path.join(home, ".local", "share")), "scAnnoRare")
    return base

if getattr(sys, "frozen", False):
    # Packaged: runner scripts are extracted into the bundle (_MEIPASS);
    # the workspace must live in a user-writable location, never inside the app bundle.
    _BUNDLE = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    WORKSPACE_DIR = os.path.join(_user_data_dir(), "workspace")
    RUNNERS_DIR = os.path.join(_BUNDLE, "runners")
else:
    _AGENT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    WORKSPACE_DIR = os.path.join(_AGENT_ROOT, "workspace")
    RUNNERS_DIR = os.path.join(_AGENT_ROOT, "runners")

os.makedirs(WORKSPACE_DIR, exist_ok=True)
JOBS_DIR = os.path.join(WORKSPACE_DIR, "jobs")
os.makedirs(JOBS_DIR, exist_ok=True)
DB_PATH = os.path.join(JOBS_DIR, "jobs.sqlite")


# Initialize jobs.sqlite db
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        task_type TEXT,
        status TEXT,
        progress INTEGER,
        config_json TEXT,
        result_json TEXT,
        created_at REAL,
        finished_at REAL
    )
    """)
    conn.commit()
    conn.close()

init_db()

# Request schemas
class AnnotationTaskRequest(BaseModel):
    filepath: str
    pred_csv_path: str
    label_col: str
    match_mode: Optional[str] = "relaxed"
    cell_id_col: Optional[str] = None

class RareTaskRequest(BaseModel):
    filepath: str
    pred_csv_path: str
    label_col: str
    rare_mode: str
    target_rare_classes: List[str]
    match_mode: Optional[str] = "relaxed"
    cell_id_col: Optional[str] = None

# DB operations
def update_job_status(job_id: str, status: str, progress: int, result: Optional[dict] = None, finished_at: Optional[float] = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if result:
        res_str = json.dumps(result, ensure_ascii=False)
        cursor.execute("UPDATE jobs SET status=?, progress=?, result_json=?, finished_at=? WHERE id=?", (status, progress, res_str, finished_at, job_id))
    else:
        cursor.execute("UPDATE jobs SET status=?, progress=? WHERE id=?", (status, progress, job_id))
    conn.commit()
    conn.close()

def log_event(job_dir: str, event_name: str, progress: int):
    # write to task_events.jsonl (25.3 task_events.jsonl format)
    events_path = os.path.join(job_dir, "task_events.jsonl")
    event = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "event": event_name,
        "progress": progress
    }
    with open(events_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

# Active running processes store (for cancellation)
active_processes: Dict[str, subprocess.Popen] = {}

def run_job_thread(job_id: str, task_type: str, args: List[str], job_dir: str):
    log_event(job_dir, "job_started", 10)
    update_job_status(job_id, "running", 10)
    
    stdout_file = open(os.path.join(job_dir, "stdout.log"), "w", encoding="utf-8")
    stderr_file = open(os.path.join(job_dir, "stderr.log"), "w", encoding="utf-8")
    
    try:
        log_event(job_dir, "dataset_loaded", 30)
        update_job_status(job_id, "running", 30)
        
        # Start runner process
        proc = subprocess.Popen(args, stdout=stdout_file, stderr=stderr_file, **_POPEN_KW)
        active_processes[job_id] = proc
        
        # Wait for finish
        proc.wait()
        
        if proc.returncode == 0:
            log_event(job_dir, "metrics_computed", 70)
            update_job_status(job_id, "running", 70)
            
            # Now trigger report generator (runners/generate_report.py)
            result_json = os.path.join(job_dir, "result.json")
            
            report_script = os.path.join(RUNNERS_DIR, "generate_report.py")

            # Run report generator
            rep_args = runner_cmd(report_script, result_json, job_dir)
            rep_proc = subprocess.Popen(rep_args, stdout=stdout_file, stderr=stderr_file, **_POPEN_KW)
            rep_proc.wait()
            
            if rep_proc.returncode == 0:
                log_event(job_dir, "report_generated", 100)
                
                # Read result.json
                with open(result_json, "r", encoding="utf-8") as f:
                    res_data = json.load(f)
                    
                update_job_status(job_id, "success", 100, result=res_data, finished_at=time.time())
                logger.info(f"Job {job_id} completed successfully.")
            else:
                log_event(job_dir, "report_generation_failed", 90)
                update_job_status(job_id, "failed", 90, result={"error": "Failed to generate HTML report."}, finished_at=time.time())
        else:
            log_event(job_dir, "execution_failed", 50)
            # Read stderr if possible to extract reason
            err_msg = "Subprocess returned non-zero code."
            update_job_status(job_id, "failed", 50, result={"error": err_msg}, finished_at=time.time())
            
    except Exception as e:
        logger.error(f"Error executing job {job_id}: {e}")
        update_job_status(job_id, "failed", 50, result={"error": str(e)}, finished_at=time.time())
    finally:
        stdout_file.close()
        stderr_file.close()
        active_processes.pop(job_id, None)

@router.post("/tasks/evaluate-annotation")
async def create_annotation_task(payload: AnnotationTaskRequest, background_tasks: BackgroundTasks):
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    job_dir = os.path.join(JOBS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    # Save job config (config.json)
    config = payload.dict()
    with open(os.path.join(job_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
        
    # Prepare runner path
    runner_script = os.path.join(RUNNERS_DIR, "evaluate_annotation.py")

    # Save job in sqlite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO jobs (id, task_type, status, progress, config_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (job_id, "annotation_evaluation", "pending", 0, json.dumps(config), time.time())
    )
    conn.commit()
    conn.close()
    
    args = runner_cmd(
        runner_script,
        payload.filepath, payload.pred_csv_path,
        payload.label_col, job_dir, payload.match_mode,
    )

    # Dispatch background execution
    background_tasks.add_task(run_job_thread, job_id, "annotation_evaluation", args, job_dir)
    
    return {
        "success": True,
        "local_job_id": job_id,
        "status": "pending",
        "message": "Annotation evaluation task queued successfully."
    }

@router.post("/tasks/evaluate-rare")
async def create_rare_task(payload: RareTaskRequest, background_tasks: BackgroundTasks):
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    job_dir = os.path.join(JOBS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    # Save config.json
    config = payload.dict()
    with open(os.path.join(job_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
        
    # Prepare runner path
    runner_script = os.path.join(RUNNERS_DIR, "evaluate_rare.py")
    
    # Save job in sqlite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO jobs (id, task_type, status, progress, config_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (job_id, "rare_detection_evaluation", "pending", 0, json.dumps(config), time.time())
    )
    conn.commit()
    conn.close()
    
    args = runner_cmd(
        runner_script,
        payload.filepath, payload.pred_csv_path,
        payload.label_col, job_dir, payload.rare_mode,
        json.dumps(payload.target_rare_classes), payload.match_mode,
    )
    
    background_tasks.add_task(run_job_thread, job_id, "rare_detection_evaluation", args, job_dir)
    
    return {
        "success": True,
        "local_job_id": job_id,
        "status": "pending",
        "message": "Rare cell detection evaluation task queued successfully."
    }

@router.get("/tasks/{local_job_id}")
async def get_task_status(local_job_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id=?", (local_job_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Job not found.")
        
    res = dict(row)
    res["config"] = json.loads(res["config_json"]) if res["config_json"] else None
    res["result"] = json.loads(res["result_json"]) if res["result_json"] else None
    return res

@router.get("/tasks/{local_job_id}/logs")
async def get_task_logs(local_job_id: str):
    log_path = os.path.join(JOBS_DIR, local_job_id, "stdout.log")
    err_path = os.path.join(JOBS_DIR, local_job_id, "stderr.log")
    events_path = os.path.join(JOBS_DIR, local_job_id, "task_events.jsonl")
    
    stdout = ""
    stderr = ""
    events = []
    
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            stdout = f.read()
    if os.path.exists(err_path):
        with open(err_path, "r", encoding="utf-8") as f:
            stderr = f.read()
    if os.path.exists(events_path):
        with open(events_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    events.append(json.loads(line.strip()))
                except Exception:
                    pass
                    
    return {
        "stdout": stdout,
        "stderr": stderr,
        "events": events
    }

@router.post("/tasks/{local_job_id}/cancel")
async def cancel_task(local_job_id: str):
    proc = active_processes.get(local_job_id)
    if proc:
        try:
            proc.terminate()
            update_job_status(local_job_id, "cancelled", 100, result={"error": "Terminated by user."}, finished_at=time.time())
            return {"success": True, "message": "Job successfully cancelled."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to terminate process: {e}")
            
    # If not active, check database status
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM jobs WHERE id=?", (local_job_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Job not found.")
        
    if row[0] in ["pending", "running"]:
        update_job_status(local_job_id, "cancelled", 100, result={"error": "Cancelled before execution."}, finished_at=time.time())
        return {"success": True, "message": "Job marked as cancelled."}
        
    return {"success": False, "message": "Job is already completed."}

@router.get("/tasks/{local_job_id}/report")
async def get_task_report(local_job_id: str):
    report_path = os.path.join(JOBS_DIR, local_job_id, "report.html")
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report HTML file does not exist yet.")
    return FileResponse(report_path, media_type="text/html")


# ── inspect-dataset (standalone task endpoint) ────────────────────────────────
class InspectDatasetRequest(BaseModel):
    filepath: str
    dataset_name: str
    label_col: str
    batch_col: Optional[str] = None
    rare_threshold: Optional[float] = 0.05


@router.post("/tasks/inspect-dataset")
async def inspect_dataset_task(payload: InspectDatasetRequest, background_tasks: BackgroundTasks):
    """Inspect h5ad file and compute label distribution / rare candidates as a tracked job."""
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    job_dir = os.path.join(JOBS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    config = payload.dict()
    with open(os.path.join(job_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO jobs (id, task_type, status, progress, config_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (job_id, "inspect_dataset", "pending", 0, json.dumps(config), time.time()),
    )
    conn.commit(); conn.close()

    def _run():
        update_job_status(job_id, "running", 20)
        log_event(job_dir, "started", 20)
        try:
            import anndata
            import pandas as pd

            adata = anndata.read_h5ad(payload.filepath, backed="r")
            if payload.label_col not in adata.obs.columns:
                raise ValueError(f"label_col '{payload.label_col}' not found in obs.")

            obs_df = pd.DataFrame(adata.obs[[payload.label_col]])
            if payload.batch_col and payload.batch_col in adata.obs.columns:
                obs_df[payload.batch_col] = adata.obs[payload.batch_col]

            invalid = {"NaN", "None", "", "NA", "Unknown", "unknown", "unassigned", "Unassigned"}
            obs_df[payload.label_col] = obs_df[payload.label_col].astype(str).str.strip()
            valid_mask = ~obs_df[payload.label_col].isin(invalid) & obs_df[payload.label_col].notna()
            valid_df = obs_df[valid_mask]

            total = len(obs_df)
            valid_count = len(valid_df)
            label_counts = valid_df[payload.label_col].value_counts()

            label_distribution: dict = {}
            rare_candidates: list = []
            for lbl, cnt in label_counts.items():
                ratio = float(cnt / valid_count) if valid_count else 0.0
                label_distribution[str(lbl)] = {"count": int(cnt), "ratio": round(ratio, 4)}
                if ratio < payload.rare_threshold:
                    rare_candidates.append({"class_name": str(lbl), "count": int(cnt), "ratio": round(ratio, 4)})

            batch_distribution: dict = {}
            if payload.batch_col and payload.batch_col in obs_df.columns:
                for b, cnt in obs_df[payload.batch_col].value_counts().items():
                    batch_distribution[str(b)] = {"count": int(cnt), "ratio": round(float(cnt / total), 4)}

            result = {
                "success": True,
                "task_type": "inspect_dataset",
                "dataset_name": payload.dataset_name,
                "filepath": payload.filepath,
                "n_cells": int(adata.shape[0]),
                "n_genes": int(adata.shape[1]),
                "obs_columns": list(adata.obs.columns),
                "var_columns": list(adata.var.columns),
                "total_cells": total,
                "valid_label_cells": valid_count,
                "invalid_label_cells": total - valid_count,
                "label_distribution": label_distribution,
                "rare_candidates": rare_candidates,
                "batch_distribution": batch_distribution,
            }

            result_path = os.path.join(job_dir, "result.json")
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=4, ensure_ascii=False)

            # Update local dataset registry
            registry_path = os.path.join(WORKSPACE_DIR, "datasets", "dataset_registry.json")
            os.makedirs(os.path.dirname(registry_path), exist_ok=True)
            registry: dict = {}
            if os.path.exists(registry_path):
                try:
                    with open(registry_path, "r", encoding="utf-8") as f:
                        registry = json.load(f)
                except Exception:
                    pass
            registry[payload.dataset_name] = result
            with open(registry_path, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=4, ensure_ascii=False)

            update_job_status(job_id, "success", 100, result=result, finished_at=time.time())
            log_event(job_dir, "completed", 100)
        except Exception as e:
            logger.error(f"inspect-dataset job {job_id} failed: {e}")
            update_job_status(job_id, "failed", 50, result={"error": str(e)}, finished_at=time.time())

    background_tasks.add_task(_run)
    return {"success": True, "local_job_id": job_id, "status": "pending"}


# ── generate-report (standalone task endpoint) ────────────────────────────────
class GenerateReportRequest(BaseModel):
    local_job_id: str   # ID of a completed evaluate-annotation / evaluate-rare job


@router.post("/tasks/generate-report")
async def generate_report_task(payload: GenerateReportRequest, background_tasks: BackgroundTasks):
    """(Re-)generate the HTML report for a completed evaluation job."""
    source_job_dir = os.path.join(JOBS_DIR, payload.local_job_id)
    result_json = os.path.join(source_job_dir, "result.json")
    if not os.path.exists(result_json):
        raise HTTPException(status_code=404, detail=f"result.json not found for job {payload.local_job_id}.")

    report_job_id = f"job_{uuid.uuid4().hex[:8]}"
    report_job_dir = os.path.join(JOBS_DIR, report_job_id)
    os.makedirs(report_job_dir, exist_ok=True)

    config = {"local_job_id": payload.local_job_id}
    with open(os.path.join(report_job_dir, "config.json"), "w") as f:
        json.dump(config, f)

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO jobs (id, task_type, status, progress, config_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (report_job_id, "generate_report", "pending", 0, json.dumps(config), time.time()),
    )
    conn.commit(); conn.close()

    report_script = os.path.join(RUNNERS_DIR, "generate_report.py")

    def _run():
        update_job_status(report_job_id, "running", 20)
        log_event(report_job_dir, "started", 20)
        stdout_f = open(os.path.join(report_job_dir, "stdout.log"), "w")
        stderr_f = open(os.path.join(report_job_dir, "stderr.log"), "w")
        try:
            proc = subprocess.Popen(
                runner_cmd(report_script, result_json, source_job_dir),
                stdout=stdout_f, stderr=stderr_f, **_POPEN_KW,
            )
            proc.wait()
            if proc.returncode == 0:
                result = {"success": True, "report_path": os.path.join(source_job_dir, "report.html")}
                update_job_status(report_job_id, "success", 100, result=result, finished_at=time.time())
                log_event(report_job_dir, "completed", 100)
            else:
                update_job_status(report_job_id, "failed", 90, result={"error": "Report generation failed."}, finished_at=time.time())
        except Exception as e:
            update_job_status(report_job_id, "failed", 50, result={"error": str(e)}, finished_at=time.time())
        finally:
            stdout_f.close(); stderr_f.close()

    background_tasks.add_task(_run)
    return {
        "success": True,
        "local_job_id": report_job_id,
        "source_job_id": payload.local_job_id,
        "status": "pending",
    }
