import os
import time
import uuid
import json
import logging
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.db import get_db, engine, Base
import app.models as models

Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("web-backend")

app = FastAPI(title="scAnnoRare Web Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _ensure_admin(db: Session) -> models.User:
    """Always ensure the default admin user exists, regardless of other users."""
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        admin = models.User(
            id="admin_001",
            email="admin@scannorare.com",
            username="admin",
            password_hash="admin",
            token=str(uuid.uuid4()).replace("-", ""),
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
    return admin


# ── simple token auth ─────────────────────────────────────────────────────────
def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Accept Bearer <token>; fall back to default admin for zero-config mode."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        user = db.query(models.User).filter(models.User.token == token).first()
        if user:
            return user

    return _ensure_admin(db)


@app.on_event("startup")
def _startup(db: Session = next(get_db())):
    """Ensure admin user exists on every startup."""
    _ensure_admin(db)


# ── Pydantic schemas ──────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    email: str
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class ProjectCreate(BaseModel):
    project_name: str
    description: Optional[str] = None

class ProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    description: Optional[str] = None

class DatasetCreate(BaseModel):
    project_id: Optional[str] = None
    dataset_name: str
    local_dataset_alias: str
    label_col: Optional[str] = None
    batch_col: Optional[str] = None
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
    project_id: Optional[str] = None
    dataset_id: str
    experiment_name: str
    task_type: str
    label_col: str
    batch_col: Optional[str] = None
    rare_mode: Optional[str] = None
    rare_threshold: Optional[float] = None
    target_rare_classes: Optional[List[str]] = None

class ExperimentUpdate(BaseModel):
    experiment_name: Optional[str] = None
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

class TriggerJobRequest(BaseModel):
    method_run_id: str
    agent_url: str = "http://127.0.0.1:17890"
    session_token: str


# ── Auth ──────────────────────────────────────────────────────────────────────
@app.post("/api/v1/auth/register")
async def register(payload: UserRegister, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already registered.")
    user = models.User(
        id=f"user_{uuid.uuid4().hex[:8]}",
        email=payload.email,
        username=payload.username,
        password_hash=payload.password,
        token=str(uuid.uuid4()).replace("-", ""),
    )
    db.add(user)
    db.commit()
    return {"success": True, "message": "Registered successfully."}


@app.post("/api/v1/auth/login")
async def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user or user.password_hash != payload.password:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return {
        "success": True,
        "token": user.token,
        "user": {"id": user.id, "username": user.username, "email": user.email},
    }


@app.get("/api/v1/auth/me")
async def get_me(user: models.User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "email": user.email}


# ── Projects ──────────────────────────────────────────────────────────────────
@app.get("/api/v1/projects")
async def list_projects(page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):
    q = db.query(models.Project)
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_proj(p) for p in items], "total": total, "page": page, "page_size": page_size}


@app.post("/api/v1/projects")
async def create_project(payload: ProjectCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    p = models.Project(
        id=f"proj_{uuid.uuid4().hex[:8]}",
        user_id=user.id,
        project_name=payload.project_name,
        description=payload.description,
    )
    db.add(p); db.commit(); db.refresh(p)
    return {"success": True, "project": _proj(p)}


@app.get("/api/v1/projects/{project_id}")
async def get_project(project_id: str, db: Session = Depends(get_db)):
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found.")
    return _proj(p)


@app.put("/api/v1/projects/{project_id}")
async def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)):
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found.")
    if payload.project_name is not None:
        p.project_name = payload.project_name
    if payload.description is not None:
        p.description = payload.description
    p.updated_at = time.time()
    db.commit()
    return {"success": True, "project": _proj(p)}


@app.delete("/api/v1/projects/{project_id}")
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found.")
    db.delete(p); db.commit()
    return {"success": True}


def _proj(p):
    return {"id": p.id, "user_id": p.user_id, "project_name": p.project_name,
            "description": p.description, "created_at": p.created_at}


# ── Datasets ──────────────────────────────────────────────────────────────────
def _ds(d):
    return {
        "id": d.id, "project_id": d.project_id, "dataset_name": d.dataset_name,
        "local_dataset_alias": d.local_dataset_alias,
        "label_col": d.label_col, "batch_col": d.batch_col,
        "n_cells": d.n_cells, "n_genes": d.n_genes,
        "obs_columns": json.loads(d.obs_columns_json),
        "var_columns": json.loads(d.var_columns_json),
        "label_distribution": json.loads(d.label_distribution_json),
        "rare_candidates": json.loads(d.rare_candidates_json),
        "created_at": d.created_at,
    }


@app.get("/api/v1/datasets")
async def list_datasets(db: Session = Depends(get_db)):
    return [_ds(d) for d in db.query(models.Dataset).all()]


@app.post("/api/v1/datasets")
async def create_dataset(payload: DatasetCreate, db: Session = Depends(get_db)):
    d = models.Dataset(
        id=f"data_{uuid.uuid4().hex[:8]}",
        project_id=payload.project_id,
        dataset_name=payload.dataset_name,
        local_dataset_alias=payload.local_dataset_alias,
        label_col=payload.label_col,
        batch_col=payload.batch_col,
        n_cells=payload.n_cells,
        n_genes=payload.n_genes,
        obs_columns_json=json.dumps(payload.obs_columns),
        var_columns_json=json.dumps(payload.var_columns),
        label_distribution_json=json.dumps(payload.label_distribution),
        rare_candidates_json=json.dumps(payload.rare_candidates),
    )
    db.add(d); db.commit(); db.refresh(d)
    return {"success": True, "dataset_id": d.id, "dataset": _ds(d)}


@app.get("/api/v1/datasets/{dataset_id}")
async def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    d = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return _ds(d)


@app.delete("/api/v1/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str, db: Session = Depends(get_db)):
    d = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    db.delete(d); db.commit()
    return {"success": True}


# ── Agents ────────────────────────────────────────────────────────────────────
def _agent(a):
    return {
        "id": a.id, "agent_name": a.agent_name, "device_id": a.device_id,
        "os": a.os,
        "cpu_summary": json.loads(a.cpu_summary_json),
        "gpu_summary": json.loads(a.gpu_summary_json),
        "package_summary": json.loads(a.package_summary_json),
        "last_seen_at": a.last_seen_at,
        "status": "online" if (time.time() - a.last_seen_at) < 30 else "offline",
    }


@app.get("/api/v1/agents")
async def list_agents(db: Session = Depends(get_db)):
    return [_agent(a) for a in db.query(models.Agent).all()]


@app.get("/api/v1/agents/{agent_id}")
async def get_agent(agent_id: str, db: Session = Depends(get_db)):
    a = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return _agent(a)


@app.post("/api/v1/agents/register")
async def register_agent(payload: AgentRegister, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    a = db.query(models.Agent).filter(models.Agent.device_id == payload.device_id).first()
    if not a:
        a = models.Agent(id=f"agent_{uuid.uuid4().hex[:8]}", user_id=user.id, device_id=payload.device_id)
        db.add(a)
    a.agent_name = payload.agent_name
    a.os = payload.os
    a.cpu_summary_json = json.dumps(payload.cpu_summary)
    a.gpu_summary_json = json.dumps(payload.gpu_summary)
    a.package_summary_json = json.dumps(payload.package_summary)
    a.last_seen_at = time.time()
    a.status = "online"
    db.commit(); db.refresh(a)
    return {"success": True, "agent_id": a.id}


@app.post("/api/v1/agents/heartbeat")
async def agent_heartbeat(payload: AgentHeartbeat, db: Session = Depends(get_db)):
    a = db.query(models.Agent).filter(models.Agent.device_id == payload.device_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Agent not registered.")
    a.last_seen_at = time.time()
    a.status = payload.status
    db.commit()
    return {"success": True}


# ── Experiments ───────────────────────────────────────────────────────────────
def _exp(e):
    return {
        "id": e.id, "project_id": e.project_id, "dataset_id": e.dataset_id,
        "experiment_name": e.experiment_name, "task_type": e.task_type,
        "label_col": e.label_col, "batch_col": e.batch_col,
        "rare_mode": e.rare_mode, "rare_threshold": e.rare_threshold,
        "target_rare_classes": json.loads(e.target_rare_classes_json) if e.target_rare_classes_json else [],
        "created_at": e.created_at,
    }


@app.get("/api/v1/experiments")
async def list_experiments(db: Session = Depends(get_db)):
    return [_exp(e) for e in db.query(models.Experiment).all()]


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
        target_rare_classes_json=json.dumps(payload.target_rare_classes) if payload.target_rare_classes else None,
    )
    db.add(e); db.commit(); db.refresh(e)
    return {"success": True, "experiment": _exp(e)}


@app.get("/api/v1/experiments/{experiment_id}")
async def get_experiment(experiment_id: str, db: Session = Depends(get_db)):
    e = db.query(models.Experiment).filter(models.Experiment.id == experiment_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    return _exp(e)


@app.put("/api/v1/experiments/{experiment_id}")
async def update_experiment(experiment_id: str, payload: ExperimentUpdate, db: Session = Depends(get_db)):
    e = db.query(models.Experiment).filter(models.Experiment.id == experiment_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    if payload.experiment_name is not None:
        e.experiment_name = payload.experiment_name
    if payload.rare_mode is not None:
        e.rare_mode = payload.rare_mode
    if payload.rare_threshold is not None:
        e.rare_threshold = payload.rare_threshold
    if payload.target_rare_classes is not None:
        e.target_rare_classes_json = json.dumps(payload.target_rare_classes)
    e.updated_at = time.time()
    db.commit()
    return {"success": True, "experiment": _exp(e)}


@app.delete("/api/v1/experiments/{experiment_id}")
async def delete_experiment(experiment_id: str, db: Session = Depends(get_db)):
    e = db.query(models.Experiment).filter(models.Experiment.id == experiment_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    db.delete(e); db.commit()
    return {"success": True}


# ── Method Runs ───────────────────────────────────────────────────────────────
def _run(r):
    return {
        "id": r.id, "experiment_id": r.experiment_id, "method_name": r.method_name,
        "method_type": r.method_type, "input_type": r.input_type,
        "prediction_file_alias": r.prediction_file_alias,
        "baseline_file_alias": r.baseline_file_alias,
        "status": r.status, "created_at": r.created_at,
    }


@app.get("/api/v1/experiments/{experiment_id}/method-runs")
async def list_method_runs(experiment_id: str, db: Session = Depends(get_db)):
    return [_run(r) for r in db.query(models.MethodRun).filter(models.MethodRun.experiment_id == experiment_id).all()]


@app.post("/api/v1/experiments/{experiment_id}/method-runs")
async def create_method_run(experiment_id: str, payload: MethodRunCreate, db: Session = Depends(get_db)):
    r = models.MethodRun(
        id=f"run_{uuid.uuid4().hex[:8]}",
        experiment_id=experiment_id,
        method_name=payload.method_name,
        method_type=payload.method_type,
        input_type=payload.input_type,
        prediction_file_alias=payload.prediction_file_alias,
        baseline_file_alias=payload.baseline_file_alias,
        status="pending",
    )
    db.add(r); db.commit(); db.refresh(r)
    return {"success": True, "method_run": _run(r)}


@app.get("/api/v1/method-runs/{method_run_id}")
async def get_method_run(method_run_id: str, db: Session = Depends(get_db)):
    r = db.query(models.MethodRun).filter(models.MethodRun.id == method_run_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Method run not found.")
    return _run(r)


@app.delete("/api/v1/method-runs/{method_run_id}")
async def delete_method_run(method_run_id: str, db: Session = Depends(get_db)):
    r = db.query(models.MethodRun).filter(models.MethodRun.id == method_run_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Method run not found.")
    db.delete(r); db.commit()
    return {"success": True}


# ── Jobs ──────────────────────────────────────────────────────────────────────
import requests as _requests

def _job(j):
    return {
        "id": j.id, "experiment_id": j.experiment_id, "method_run_id": j.method_run_id,
        "job_type": j.job_type, "status": j.status, "progress": j.progress,
        "local_job_id": j.local_job_id,
        "result_summary": json.loads(j.result_summary_json) if j.result_summary_json else None,
        "created_at": j.created_at, "finished_at": j.finished_at,
    }


@app.post("/api/v1/jobs")
async def trigger_eval_job(payload: TriggerJobRequest, db: Session = Depends(get_db)):
    """Dispatch evaluation job to Local Agent via session_token in request body."""
    run = db.query(models.MethodRun).filter(models.MethodRun.id == payload.method_run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Method run not found.")

    exp = db.query(models.Experiment).filter(models.Experiment.id == run.experiment_id).first()
    dataset = db.query(models.Dataset).filter(models.Dataset.id == exp.dataset_id).first()

    headers = {
        "Authorization": f"Bearer {payload.session_token}",
        "X-scAnnoRare-Origin": "http://localhost:5173",
    }

    if exp.task_type == "annotation_evaluation":
        endpoint = "/api/v1/local/tasks/evaluate-annotation"
        agent_payload = {
            "filepath": dataset.local_dataset_alias,
            "pred_csv_path": run.prediction_file_alias,
            "label_col": exp.label_col,
            "match_mode": "relaxed",
        }
    else:
        endpoint = "/api/v1/local/tasks/evaluate-rare"
        agent_payload = {
            "filepath": dataset.local_dataset_alias,
            "pred_csv_path": run.prediction_file_alias,
            "label_col": exp.label_col,
            "rare_mode": exp.rare_mode or "pooled_rare_vs_nonrare",
            "target_rare_classes": json.loads(exp.target_rare_classes_json) if exp.target_rare_classes_json else [],
            "match_mode": "relaxed",
        }

    try:
        url = f"{payload.agent_url.rstrip('/')}{endpoint}"
        resp = _requests.post(url, json=agent_payload, headers=headers, timeout=15)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"Agent error: {resp.text}")
        local_job_id = resp.json().get("local_job_id")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot reach Local Agent: {e}")

    job = models.Job(
        id=f"job_{uuid.uuid4().hex[:8]}",
        experiment_id=exp.id,
        method_run_id=run.id,
        agent_id="local_agent",
        job_type=exp.task_type,
        status="running",
        progress=10,
        local_job_id=local_job_id,
        config_json=json.dumps(agent_payload),
    )
    db.add(job)
    run.status = "running"
    db.commit()
    return {"success": True, "job_id": job.id, "local_job_id": local_job_id}


@app.get("/api/v1/jobs/{job_id}")
async def get_job(job_id: str, db: Session = Depends(get_db)):
    j = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Job not found.")
    return _job(j)


@app.get("/api/v1/jobs/{job_id}/logs")
async def get_job_logs(job_id: str, session_token: str, agent_url: str = "http://127.0.0.1:17890", db: Session = Depends(get_db)):
    j = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not j or not j.local_job_id:
        raise HTTPException(status_code=404, detail="Job not found or no local job ID.")
    try:
        resp = _requests.get(
            f"{agent_url}/api/v1/local/tasks/{j.local_job_id}/logs",
            headers={"Authorization": f"Bearer {session_token}"},
            timeout=10,
        )
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot reach Agent: {e}")


@app.post("/api/v1/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, session_token: str, agent_url: str = "http://127.0.0.1:17890", db: Session = Depends(get_db)):
    j = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not j or not j.local_job_id:
        raise HTTPException(status_code=404, detail="Job not found.")
    try:
        _requests.post(
            f"{agent_url}/api/v1/local/tasks/{j.local_job_id}/cancel",
            headers={"Authorization": f"Bearer {session_token}"},
            timeout=10,
        )
    except Exception:
        pass
    j.status = "cancelled"
    db.commit()
    return {"success": True}


@app.post("/api/v1/jobs/{job_id}/sync")
async def sync_job(job_id: str, session_token: str, agent_url: str = "http://127.0.0.1:17890", db: Session = Depends(get_db)):
    j = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Job not found.")

    try:
        resp = _requests.get(
            f"{agent_url}/api/v1/local/tasks/{j.local_job_id}",
            headers={"Authorization": f"Bearer {session_token}"},
            timeout=10,
        )
        agent_job = resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot reach Agent: {e}")

    agent_status = agent_job.get("status")
    progress = agent_job.get("progress", 0)
    j.status = agent_status
    j.progress = progress

    if agent_status == "success":
        result_data = agent_job.get("result", {})
        j.result_summary_json = json.dumps(result_data)
        if j.finished_at is None:
            j.finished_at = time.time()

        existing = db.query(models.MethodResult).filter(models.MethodResult.method_run_id == j.method_run_id).first()
        if not existing:
            mr = models.MethodResult(
                id=f"res_{uuid.uuid4().hex[:8]}",
                method_run_id=j.method_run_id,
                job_id=j.id,
                metrics_json=json.dumps(result_data.get("overall_metrics", {})),
                per_class_metrics_json=json.dumps(result_data.get("per_class_metrics", {})),
                rare_metrics_json=json.dumps(result_data.get("overall_metrics", {})) if "rare" in j.job_type else None,
                confusion_matrix_json=json.dumps(result_data.get("confusion_matrix", {})),
                curve_data_json=json.dumps({
                    "roc_curve": result_data.get("overall_metrics", {}).get("roc_curve"),
                    "pr_curve": result_data.get("overall_metrics", {}).get("pr_curve"),
                }) if "rare" in j.job_type else None,
            )
            db.add(mr)

            # Save report record
            report = models.Report(
                id=f"rep_{uuid.uuid4().hex[:8]}",
                experiment_id=j.experiment_id,
                method_run_id=j.method_run_id,
                job_id=j.id,
                report_type="html",
                report_path=f"local_agent::{j.local_job_id}",
                metrics_json=json.dumps(result_data.get("overall_metrics", {})),
                figures_json=json.dumps({}),
            )
            db.add(report)

        run = db.query(models.MethodRun).filter(models.MethodRun.id == j.method_run_id).first()
        if run:
            run.status = "success"

    elif agent_status in ("failed", "cancelled"):
        run = db.query(models.MethodRun).filter(models.MethodRun.id == j.method_run_id).first()
        if run:
            run.status = agent_status

    db.commit()
    return {"success": True, "status": agent_status, "progress": progress}


# ── Results & Comparison ──────────────────────────────────────────────────────
@app.get("/api/v1/method-runs/{method_run_id}/result")
async def get_method_run_result(method_run_id: str, db: Session = Depends(get_db)):
    res = db.query(models.MethodResult).filter(models.MethodResult.method_run_id == method_run_id).first()
    if not res:
        raise HTTPException(status_code=404, detail="Result not found.")
    return {
        "metrics": json.loads(res.metrics_json),
        "per_class_metrics": json.loads(res.per_class_metrics_json),
        "confusion_matrix": json.loads(res.confusion_matrix_json),
        "curve_data": json.loads(res.curve_data_json) if res.curve_data_json else None,
    }


@app.get("/api/v1/experiments/{experiment_id}/comparison")
async def get_comparison(experiment_id: str, db: Session = Depends(get_db)):
    runs = db.query(models.MethodRun).filter(
        models.MethodRun.experiment_id == experiment_id,
        models.MethodRun.status == "success",
    ).all()
    table = []
    for r in runs:
        res = db.query(models.MethodResult).filter(models.MethodResult.method_run_id == r.id).first()
        if not res:
            continue
        m = json.loads(res.metrics_json)
        table.append({
            "method_run_id": r.id,
            "method_name": r.method_name,
            "accuracy": m.get("accuracy", "N/A"),
            "macro_f1": m.get("macro_f1", "N/A"),
            "weighted_f1": m.get("weighted_f1", "N/A"),
            "rare_precision": m.get("rare_precision", "N/A"),
            "rare_recall": m.get("rare_recall", "N/A"),
            "rare_f1": m.get("rare_f1", "N/A"),
            "auprc": m.get("auprc", "N/A"),
            "auroc": m.get("auroc", "N/A"),
        })
    return {"experiment_id": experiment_id, "comparison_table": table}


@app.get("/api/v1/experiments/{experiment_id}/comparison/export")
async def export_comparison(experiment_id: str, db: Session = Depends(get_db)):
    data = await get_comparison(experiment_id, db)
    import csv, io
    output = io.StringIO()
    if data["comparison_table"]:
        writer = csv.DictWriter(output, fieldnames=data["comparison_table"][0].keys())
        writer.writeheader()
        writer.writerows(data["comparison_table"])
    from fastapi.responses import Response
    return Response(content=output.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=comparison_{experiment_id}.csv"})


# ── Reports ───────────────────────────────────────────────────────────────────
def _report(r):
    return {
        "id": r.id, "experiment_id": r.experiment_id, "method_run_id": r.method_run_id,
        "job_id": r.job_id, "report_type": r.report_type, "report_path": r.report_path,
        "metrics": json.loads(r.metrics_json) if r.metrics_json else {},
        "created_at": r.created_at,
    }


@app.get("/api/v1/reports")
async def list_reports(experiment_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.Report)
    if experiment_id:
        q = q.filter(models.Report.experiment_id == experiment_id)
    return [_report(r) for r in q.all()]


@app.get("/api/v1/reports/{report_id}")
async def get_report(report_id: str, db: Session = Depends(get_db)):
    r = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found.")
    return _report(r)


@app.get("/api/v1/reports/{report_id}/download")
async def download_report(report_id: str, session_token: str, agent_url: str = "http://127.0.0.1:17890", db: Session = Depends(get_db)):
    r = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found.")
    # Proxy from Local Agent
    if r.report_path.startswith("local_agent::"):
        local_job_id = r.report_path.split("::", 1)[1]
        try:
            resp = _requests.get(
                f"{agent_url}/api/v1/local/tasks/{local_job_id}/report",
                headers={"Authorization": f"Bearer {session_token}"},
                timeout=15,
            )
            from fastapi.responses import Response
            return Response(content=resp.content, media_type="text/html")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Cannot fetch report from Agent: {e}")
    raise HTTPException(status_code=404, detail="Report file not accessible.")


# ── Summary stats (for Dashboard) ────────────────────────────────────────────
@app.get("/api/v1/stats/summary")
async def get_summary(db: Session = Depends(get_db)):
    return {
        "total_datasets": db.query(models.Dataset).count(),
        "total_experiments": db.query(models.Experiment).count(),
        "total_method_runs": db.query(models.MethodRun).count(),
        "successful_runs": db.query(models.MethodRun).filter(models.MethodRun.status == "success").count(),
        "total_reports": db.query(models.Report).count(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
