import os
import json
import uuid
import time
import sqlite3
import logging
import threading
import subprocess
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from fastapi.responses import FileResponse

logger = logging.getLogger("local-agent.tasks")
router = APIRouter()

# Get workspace directory
WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "workspace")
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
        proc = subprocess.Popen(args, stdout=stdout_file, stderr=stderr_file)
        active_processes[job_id] = proc
        
        # Wait for finish
        proc.wait()
        
        if proc.returncode == 0:
            log_event(job_dir, "metrics_computed", 70)
            update_job_status(job_id, "running", 70)
            
            # Now trigger report generator (runners/generate_report.py)
            result_json = os.path.join(job_dir, "result.json")
            
            report_script = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                "runners", "generate_report.py"
            )
            
            # Run report generator
            rep_args = ["python", report_script, result_json, job_dir]
            rep_proc = subprocess.Popen(rep_args, stdout=stdout_file, stderr=stderr_file)
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
    runner_script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
        "runners", "evaluate_annotation.py"
    )
    
    # Save job in sqlite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO jobs (id, task_type, status, progress, config_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (job_id, "annotation_evaluation", "pending", 0, json.dumps(config), time.time())
    )
    conn.commit()
    conn.close()
    
    args = [
        "python", runner_script, 
        payload.filepath, payload.pred_csv_path, 
        payload.label_col, job_dir, payload.match_mode
    ]
    
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
    runner_script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
        "runners", "evaluate_rare.py"
    )
    
    # Save job in sqlite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO jobs (id, task_type, status, progress, config_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (job_id, "rare_detection_evaluation", "pending", 0, json.dumps(config), time.time())
    )
    conn.commit()
    conn.close()
    
    args = [
        "python", runner_script, 
        payload.filepath, payload.pred_csv_path, 
        payload.label_col, job_dir, payload.rare_mode,
        json.dumps(payload.target_rare_classes), payload.match_mode
    ]
    
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
