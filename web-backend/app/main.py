import os
import time
import uuid
import json
import logging
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.db import get_db, engine, Base
import app.models as models

# Initialize Database tables
Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("web-backend")

app = FastAPI(title="scAnnoRare Web Platform", version="1.0.0")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock user security check (simple token auth for single user locally)
# In V1.0 benchmark, we default to a system admin user
def get_current_user(db: Session = Depends(get_db)):
    user = db.query(models.User).first()
    if not user:
        # Auto create default user for convenience
        user = models.User(
            id="admin_001",
            email="admin@scannorare.com",
            username="admin",
            password_hash="hashed_default"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

# --- Pydantic Schemas ---
class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class ProjectCreate(BaseModel):
    project_name: str
    description: Optional[str] = None

class DatasetCreate(BaseModel):
    project_id: str
    dataset_name: str
    local_dataset_alias: str
    n_cells: int
    n_genes: int
    obs_columns: List[str]
    var_columns: List[str]
    label_distribution: Dict[str, Any]
    rare_candidates: List[Dict[str, Any]]

class AgentRegister(BaseModel):
    agent_name: str
    device_id: str
    os: str
    cpu_summary: Dict[str, Any]
    gpu_summary: Dict[str, Any]
    package_summary: Dict[str, Any]

class AgentHeartbeat(BaseModel):
    device_id: str
    status: str

class ExperimentCreate(BaseModel):
    project_id: str
    dataset_id: str
    experiment_name: str
    task_type: str
    label_col: str
    batch_col: Optional[str] = None
    rare_mode: Optional[str] = None
    rare_threshold: Optional[float] = None
    target_rare_classes: Optional[List[str]] = None

class MethodRunCreate(BaseModel):
    experiment_id: str
    method_name: str
    method_type: str
    input_type: str
    prediction_file_alias: str
    baseline_file_alias: Optional[str] = None

# --- REST APIs (21. API Design) ---

# Auth
@app.post("/api/v1/auth/register")
async def register(payload: UserRegister, db: Session = Depends(get_db)):
    exist = db.query(models.User).filter(models.User.username == payload.username).first()
    if exist:
        raise HTTPException(status_code=400, detail="Username already registered.")
    
    user = models.User(
        id=f"user_{uuid.uuid4().hex[:8]}",
        email=payload.email,
        username=payload.username,
        password_hash=payload.password  # Mock hash
    )
    db.add(user)
    db.commit()
    return {"success": True, "message": "User registered successfully."}

@app.post("/api/v1/auth/login")
async def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user or user.password_hash != payload.password:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return {
        "success": True, 
        "token": f"mock_jwt_{user.id}", 
        "user": {"id": user.id, "username": user.username, "email": user.email}
    }

@app.get("/api/v1/auth/me")
async def get_me(user: models.User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "email": user.email}

# Projects
@app.get("/api/v1/projects")
async def list_projects(page: int = 1, page_size: int = 10, db: Session = Depends(get_db)):
    # 21.3 Pagination support
    query = db.query(models.Project)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }

@app.post("/api/v1/projects")
async def create_project(payload: ProjectCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    proj = models.Project(
        id=f"proj_{uuid.uuid4().hex[:8]}",
        user_id=user.id,
        project_name=payload.project_name,
        description=payload.description
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return {"success": True, "project": proj}

@app.get("/api/v1/projects/{project_id}")
async def get_project(project_id: str, db: Session = Depends(get_db)):
    proj = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found.")
    return proj

@app.delete("/api/v1/projects/{project_id}")
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    proj = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found.")
    db.delete(proj)
    db.commit()
    return {"success": True}

# Datasets
@app.get("/api/v1/datasets")
async def list_datasets(db: Session = Depends(get_db)):
    datasets = db.query(models.Dataset).all()
    res = []
    for d in datasets:
        item = dict(d.__dict__)
        item.pop('_sa_instance_state', None)
        item["obs_columns"] = json.loads(d.obs_columns_json)
        item["var_columns"] = json.loads(d.var_columns_json)
        item["label_distribution"] = json.loads(d.label_distribution_json)
        item["rare_candidates"] = json.loads(d.rare_candidates_json)
        res.append(item)
    return res

@app.post("/api/v1/datasets")
async def create_dataset(payload: DatasetCreate, db: Session = Depends(get_db)):
    d = models.Dataset(
        id=f"data_{uuid.uuid4().hex[:8]}",
        project_id=payload.project_id,
        dataset_name=payload.dataset_name,
        local_dataset_alias=payload.local_dataset_alias,
        n_cells=payload.n_cells,
        n_genes=payload.n_genes,
        obs_columns_json=json.dumps(payload.obs_columns),
        var_columns_json=json.dumps(payload.var_columns),
        label_distribution_json=json.dumps(payload.label_distribution),
        rare_candidates_json=json.dumps(payload.rare_candidates)
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return {"success": True, "dataset_id": d.id}

@app.get("/api/v1/datasets/{dataset_id}")
async def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    d = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    item = dict(d.__dict__)
    item.pop('_sa_instance_state', None)
    item["obs_columns"] = json.loads(d.obs_columns_json)
    item["var_columns"] = json.loads(d.var_columns_json)
    item["label_distribution"] = json.loads(d.label_distribution_json)
    item["rare_candidates"] = json.loads(d.rare_candidates_json)
    return item

# Agents
# Store paired session tokens in memory to acts as Redis (device online registry)
paired_agents_store: Dict[str, Dict[str, Any]] = {}

@app.get("/api/v1/agents")
async def list_agents(db: Session = Depends(get_db)):
    agents = db.query(models.Agent).all()
    res = []
    for a in agents:
        item = dict(a.__dict__)
        item.pop('_sa_instance_state', None)
        item["cpu_summary"] = json.loads(a.cpu_summary_json)
        item["gpu_summary"] = json.loads(a.gpu_summary_json)
        item["package_summary"] = json.loads(a.package_summary_json)
        # Determine if online based on last seen heartbeat (within 30 seconds)
        is_online = (time.time() - a.last_seen_at) < 30.0
        item["status"] = "online" if is_online else "offline"
        res.append(item)
    return res

@app.post("/api/v1/agents/register")
async def register_agent(payload: AgentRegister, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    agent = db.query(models.Agent).filter(models.Agent.device_id == payload.device_id).first()
    if not agent:
        agent = models.Agent(
            id=f"agent_{uuid.uuid4().hex[:8]}",
            user_id=user.id,
            device_id=payload.device_id
        )
        db.add(agent)
    
    agent.agent_name = payload.agent_name
    agent.os = payload.os
    agent.cpu_summary_json = json.dumps(payload.cpu_summary)
    agent.gpu_summary_json = json.dumps(payload.gpu_summary)
    agent.package_summary_json = json.dumps(payload.package_summary)
    agent.last_seen_at = time.time()
    agent.status = "online"
    
    db.commit()
    db.refresh(agent)
    return {"success": True, "agent_id": agent.id}

@app.post("/api/v1/agents/heartbeat")
async def agent_heartbeat(payload: AgentHeartbeat, db: Session = Depends(get_db)):
    agent = db.query(models.Agent).filter(models.Agent.device_id == payload.device_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent device not registered.")
    agent.last_seen_at = time.time()
    agent.status = payload.status
    db.commit()
    return {"success": True}

# Experiments
@app.get("/api/v1/experiments")
async def list_experiments(db: Session = Depends(get_db)):
    exps = db.query(models.Experiment).all()
    res = []
    for e in exps:
        item = dict(e.__dict__)
        item.pop('_sa_instance_state', None)
        item["target_rare_classes"] = json.loads(e.target_rare_classes_json) if e.target_rare_classes_json else []
        res.append(item)
    return res

@app.post("/api/v1/experiments")
async def create_experiment(payload: ExperimentCreate, db: Session = Depends(get_db)):
    e = models.Experiment(
        id=f"exp_{uuid.uuid4().hex[:8]}",
        project_id=payload.project_id,
        dataset_id=payload.dataset_id,
        experiment_name=payload.experiment_name,
        task_type=payload.task_type,
        label_col=payload.label_col,
        batch_col=payload.batch_col,
        rare_mode=payload.rare_mode,
        rare_threshold=payload.rare_threshold,
        target_rare_classes_json=json.dumps(payload.target_rare_classes) if payload.target_rare_classes else None
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return {"success": True, "experiment": e}

@app.get("/api/v1/experiments/{experiment_id}")
async def get_experiment(experiment_id: str, db: Session = Depends(get_db)):
    e = db.query(models.Experiment).filter(models.Experiment.id == experiment_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    item = dict(e.__dict__)
    item.pop('_sa_instance_state', None)
    item["target_rare_classes"] = json.loads(e.target_rare_classes_json) if e.target_rare_classes_json else []
    return item

# Method Runs
@app.get("/api/v1/experiments/{experiment_id}/method-runs")
async def list_method_runs(experiment_id: str, db: Session = Depends(get_db)):
    runs = db.query(models.MethodRun).filter(models.MethodRun.experiment_id == experiment_id).all()
    return runs

@app.post("/api/v1/experiments/{experiment_id}/method-runs")
async def create_method_run(experiment_id: str, payload: MethodRunCreate, db: Session = Depends(get_db)):
    run = models.MethodRun(
        id=f"run_{uuid.uuid4().hex[:8]}",
        experiment_id=experiment_id,
        method_name=payload.method_name,
        method_type=payload.method_type,
        input_type=payload.input_type,
        prediction_file_alias=payload.prediction_file_alias,
        baseline_file_alias=payload.baseline_file_alias,
        status="pending"
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return {"success": True, "method_run": run}

# Trigger a Job on Agent & Sync results (9.3 Annotation evaluation, 9.4 Rare evaluation)
import requests

@app.post("/api/v1/jobs")
async def trigger_eval_job(method_run_id: str, agent_url: str = "http://127.0.0.1:17890", session_token: str = None, db: Session = Depends(get_db)):
    """
    Dispatcher: Tell the Local Agent to start computation, register a Local Job, and start synchronization.
    """
    run = db.query(models.MethodRun).filter(models.MethodRun.id == method_run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Method run not found.")
        
    exp = db.query(models.Experiment).filter(models.Experiment.id == run.experiment_id).first()
    dataset = db.query(models.Dataset).filter(models.Dataset.id == exp.dataset_id).first()
    
    headers = {}
    if session_token:
        headers["Authorization"] = f"Bearer {session_token}"
        headers["X-scAnnoRare-Origin"] = "http://localhost:5173"
        
    # Build payload to agent depending on task type
    task_endpoint = ""
    agent_payload = {}
    
    if exp.task_type == "annotation_evaluation":
        task_endpoint = "/api/v1/local/tasks/evaluate-annotation"
        agent_payload = {
            "filepath": dataset.local_dataset_alias,
            "pred_csv_path": run.prediction_file_alias,
            "label_col": exp.label_col,
            "match_mode": "relaxed"
        }
    elif exp.task_type == "rare_detection_evaluation":
        task_endpoint = "/api/v1/local/tasks/evaluate-rare"
        agent_payload = {
            "filepath": dataset.local_dataset_alias,
            "pred_csv_path": run.prediction_file_alias,
            "label_col": exp.label_col,
            "rare_mode": exp.rare_mode or "pooled_rare_vs_nonrare",
            "target_rare_classes": json.loads(exp.target_rare_classes_json) if exp.target_rare_classes_json else [],
            "match_mode": "relaxed"
        }
        
    try:
        url = f"{agent_url.rstrip('/')}{task_endpoint}"
        logger.info(f"Dispatching task to Agent: {url} with {agent_payload}")
        
        response = requests.post(url, json=agent_payload, headers=headers, timeout=10)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Agent error: {response.text}")
            
        res_json = response.json()
        local_job_id = res_json.get("local_job_id")
        
        # Create Job in Web DB
        job = models.Job(
            id=f"job_{uuid.uuid4().hex[:8]}",
            experiment_id=exp.id,
            method_run_id=run.id,
            agent_id="local_agent",
            job_type=exp.task_type,
            status="running",
            progress=10,
            local_job_id=local_job_id,
            config_json=json.dumps(agent_payload)
        )
        db.add(job)
        
        # Update method run status
        run.status = "running"
        db.commit()
        
        return {
            "success": True,
            "job_id": job.id,
            "local_job_id": local_job_id,
            "message": "Evaluation job successfully dispatched to local agent."
        }
    except Exception as e:
        logger.error(f"Failed to connect to local agent: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger job on Local Agent: {str(e)}")

# Sync Job status from Local Agent
@app.post("/api/v1/jobs/{job_id}/sync")
async def sync_job_status(job_id: str, agent_url: str = "http://127.0.0.1:17890", session_token: str = None, db: Session = Depends(get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
        
    headers = {}
    if session_token:
        headers["Authorization"] = f"Bearer {session_token}"
        
    try:
        url = f"{agent_url.rstrip('/')}/api/v1/local/tasks/{job.local_job_id}"
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to poll job status from agent.")
            
        agent_job = response.json()
        status_on_agent = agent_job.get("status")
        progress = agent_job.get("progress", 0)
        
        job.status = status_on_agent
        job.progress = progress
        
        # If successfully completed, pull metrics and save to results
        if status_on_agent == "success":
            result_data = agent_job.get("result", {})
            job.result_summary_json = json.dumps(result_data)
            
            # Save into method_results table
            exist_result = db.query(models.MethodResult).filter(models.MethodResult.method_run_id == job.method_run_id).first()
            if not exist_result:
                m_res = models.MethodResult(
                    id=f"res_{uuid.uuid4().hex[:8]}",
                    method_run_id=job.method_run_id,
                    job_id=job.id,
                    metrics_json=json.dumps(result_data.get("overall_metrics", {})),
                    per_class_metrics_json=json.dumps(result_data.get("per_class_metrics", {})),
                    rare_metrics_json=json.dumps(result_data.get("overall_metrics", {})) if "rare" in job.job_type else None,
                    confusion_matrix_json=json.dumps(result_data.get("confusion_matrix", {})),
                    curve_data_json=json.dumps({
                        "roc_curve": result_data.get("overall_metrics", {}).get("roc_curve"),
                        "pr_curve": result_data.get("overall_metrics", {}).get("pr_curve")
                    }) if "rare" in job.job_type else None
                )
                db.add(m_res)
                
            # Update method_run status
            run = db.query(models.MethodRun).filter(models.MethodRun.id == job.method_run_id).first()
            if run:
                run.status = "success"
                
        elif status_on_agent == "failed":
            run = db.query(models.MethodRun).filter(models.MethodRun.id == job.method_run_id).first()
            if run:
                run.status = "failed"
                
        db.commit()
        return {"success": True, "status": status_on_agent, "progress": progress}
    except Exception as e:
        logger.error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync with local agent: {e}")

# Method Results & Comparisons (8.2 Multi-method comparative aggregation)
@app.get("/api/v1/experiments/{experiment_id}/comparison")
async def get_experiments_comparison(experiment_id: str, db: Session = Depends(get_db)):
    """
    Gathers all successful method runs under this experiment and compiles a ranking table (8.3 Comparison table)
    """
    runs = db.query(models.MethodRun).filter(
        models.MethodRun.experiment_id == experiment_id,
        models.MethodRun.status == "success"
    ).all()
    
    table_items = []
    for r in runs:
        res = db.query(models.MethodResult).filter(models.MethodResult.method_run_id == r.id).first()
        if not res:
            continue
            
        metrics = json.loads(res.metrics_json)
        
        # Gather all specs standard formatting (8.3 Comparison format)
        table_items.append({
            "method_run_id": r.id,
            "method_name": r.method_name,
            "accuracy": metrics.get("accuracy", "N/A"),
            "macro_f1": metrics.get("macro_f1", "N/A"),
            "rare_precision": metrics.get("rare_precision", "N/A"),
            "rare_recall": metrics.get("rare_recall", "N/A"),
            "rare_f1": metrics.get("rare_f1", "N/A"),
            "auprc": metrics.get("auprc", "N/A"),
            "auroc": metrics.get("auroc", "N/A"),
        })
        
    return {
        "experiment_id": experiment_id,
        "comparison_table": table_items
    }

# Single run details
@app.get("/api/v1/method-runs/{method_run_id}/result")
async def get_method_run_result(method_run_id: str, db: Session = Depends(get_db)):
    res = db.query(models.MethodResult).filter(models.MethodResult.method_run_id == method_run_id).first()
    if not res:
        raise HTTPException(status_code=404, detail="Result not computed or failed.")
        
    return {
        "metrics": json.loads(res.metrics_json),
        "per_class_metrics": json.loads(res.per_class_metrics_json),
        "confusion_matrix": json.loads(res.confusion_matrix_json),
        "curve_data": json.loads(res.curve_data_json) if res.curve_data_json else None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
