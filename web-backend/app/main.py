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
from app.auth import hash_password, verify_password, create_token, decode_token

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
    """确保默认管理员存在（密码 bcrypt 哈希存储），便于零配置首次登录。"""
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        admin = models.User(
            id="admin_001",
            email="admin@scannorare.com",
            username="admin",
            password_hash=hash_password("admin"),
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
    return admin


# ── JWT 鉴权 ──────────────────────────────────────────────────────────────────
def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> models.User:
    """要求有效的 Bearer JWT，否则 401。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录或缺少访问令牌。")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="令牌无效或已过期，请重新登录。")
    user = db.query(models.User).filter(models.User.id == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在。")
    return user


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
    config: Optional[Dict[str, Any]] = None

class TriggerJobRequest(BaseModel):
    method_run_id: str
    agent_url: str = "http://127.0.0.1:17890"
    session_token: str


# ── Auth ──────────────────────────────────────────────────────────────────────
@app.post("/api/v1/auth/register")
async def register(payload: UserRegister, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="用户名已被注册。")
    user = models.User(
        id=f"user_{uuid.uuid4().hex[:8]}",
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    return {"success": True, "message": "注册成功。"}


@app.post("/api/v1/auth/login")
async def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误。")

    # 兼容迁移：旧明文密码登录成功后顺手升级为 bcrypt 哈希。
    if not (user.password_hash or "").startswith("$2"):
        user.password_hash = hash_password(payload.password)
        db.commit()

    token = create_token(user.id, user.username)
    return {
        "success": True,
        "token": token,
        "user": {"id": user.id, "username": user.username, "email": user.email},
    }


@app.get("/api/v1/auth/me")
async def get_me(user: models.User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "email": user.email}


class ChangePassword(BaseModel):
    old_password: str
    new_password: str


@app.post("/api/v1/auth/change-password")
async def change_password(payload: ChangePassword, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误。")
    if len(payload.new_password) < 4:
        raise HTTPException(status_code=400, detail="新密码至少 4 位。")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"success": True, "message": "密码已修改，请用新密码重新登录。"}


# ── Projects ──────────────────────────────────────────────────────────────────
@app.get("/api/v1/projects")
async def list_projects(page: int = 1, page_size: int = 20, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    q = db.query(models.Project).filter(models.Project.user_id == user.id)
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


def _owned_project(project_id: str, db: Session, user: models.User) -> models.Project:
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在。")
    if p.user_id and p.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该项目。")
    return p


@app.get("/api/v1/projects/{project_id}")
async def get_project(project_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return _proj(_owned_project(project_id, db, user))


@app.put("/api/v1/projects/{project_id}")
async def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    p = _owned_project(project_id, db, user)
    if payload.project_name is not None:
        p.project_name = payload.project_name
    if payload.description is not None:
        p.description = payload.description
    p.updated_at = time.time()
    db.commit()
    return {"success": True, "project": _proj(p)}


@app.delete("/api/v1/projects/{project_id}")
async def delete_project(project_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    p = _owned_project(project_id, db, user)
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
async def list_datasets(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    rows = db.query(models.Dataset).filter(models.Dataset.user_id == user.id).all()
    return [_ds(d) for d in rows]


@app.post("/api/v1/datasets")
async def create_dataset(payload: DatasetCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    d = models.Dataset(
        id=f"data_{uuid.uuid4().hex[:8]}",
        user_id=user.id,
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


def _owned_dataset(dataset_id: str, db: Session, user: models.User) -> models.Dataset:
    d = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="数据集不存在。")
    if d.user_id and d.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该数据集。")
    return d


@app.get("/api/v1/datasets/{dataset_id}")
async def get_dataset(dataset_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return _ds(_owned_dataset(dataset_id, db, user))


@app.delete("/api/v1/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    d = _owned_dataset(dataset_id, db, user)
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
async def list_experiments(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return [_exp(e) for e in db.query(models.Experiment).filter(models.Experiment.user_id == user.id).all()]


@app.post("/api/v1/experiments")
async def create_experiment(payload: ExperimentCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    e = models.Experiment(
        id=f"exp_{uuid.uuid4().hex[:8]}",
        user_id=user.id,
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


def _owned_experiment(experiment_id: str, db: Session, user: models.User) -> models.Experiment:
    e = db.query(models.Experiment).filter(models.Experiment.id == experiment_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="实验不存在。")
    if e.user_id and e.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该实验。")
    return e


@app.get("/api/v1/experiments/{experiment_id}")
async def get_experiment(experiment_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return _exp(_owned_experiment(experiment_id, db, user))


@app.put("/api/v1/experiments/{experiment_id}")
async def update_experiment(experiment_id: str, payload: ExperimentUpdate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    e = _owned_experiment(experiment_id, db, user)
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
async def delete_experiment(experiment_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    e = _owned_experiment(experiment_id, db, user)
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
async def list_method_runs(experiment_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _owned_experiment(experiment_id, db, user)
    return [_run(r) for r in db.query(models.MethodRun).filter(models.MethodRun.experiment_id == experiment_id).all()]


@app.post("/api/v1/experiments/{experiment_id}/method-runs")
async def create_method_run(experiment_id: str, payload: MethodRunCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _owned_experiment(experiment_id, db, user)
    r = models.MethodRun(
        id=f"run_{uuid.uuid4().hex[:8]}",
        experiment_id=experiment_id,
        method_name=payload.method_name,
        method_type=payload.method_type,
        input_type=payload.input_type,
        prediction_file_alias=payload.prediction_file_alias,
        baseline_file_alias=payload.baseline_file_alias,
        config_json=json.dumps(payload.config) if payload.config else None,
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

    if run.method_type == "builtin_celltypist":
        # 内置方法运行：无需预测 CSV，Agent 直接对 h5ad 跑 CellTypist 再评估
        cfg = json.loads(run.config_json) if run.config_json else {}
        endpoint = "/api/v1/local/tasks/run-celltypist"
        agent_payload = {
            "filepath": dataset.local_dataset_alias,
            "label_col": exp.label_col,
            "model": cfg.get("model", "Immune_All_Low.pkl"),
            "match_mode": "relaxed",
        }
    elif exp.task_type == "annotation_evaluation":
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


@app.post("/api/v1/method-runs/{method_run_id}/result")
async def write_method_run_result(
    method_run_id: str,
    result_data: dict,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """外部方法（scANVI 等）完成后，由前端将 Agent 的 result JSON 写回数据库。"""
    run = db.query(models.MethodRun).filter(models.MethodRun.id == method_run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="MethodRun not found.")

    # 前端可附带 _local_job_id 以便 report 代理到 Agent 文件
    local_job_id = result_data.pop("_local_job_id", None)

    existing = db.query(models.MethodResult).filter(models.MethodResult.method_run_id == method_run_id).first()
    if existing:
        existing.metrics_json = json.dumps(result_data.get("overall_metrics", {}))
        existing.per_class_metrics_json = json.dumps(result_data.get("per_class_metrics", {}))
        existing.confusion_matrix_json = json.dumps(result_data.get("confusion_matrix", {}))
    else:
        mr = models.MethodResult(
            id=f"res_{uuid.uuid4().hex[:8]}",
            method_run_id=method_run_id,
            job_id=None,
            metrics_json=json.dumps(result_data.get("overall_metrics", {})),
            per_class_metrics_json=json.dumps(result_data.get("per_class_metrics", {})),
            confusion_matrix_json=json.dumps(result_data.get("confusion_matrix", {})),
        )
        db.add(mr)

    run.status = "success"

    report_path = f"local_agent::{local_job_id}" if local_job_id else "external_method"
    rep_exists = db.query(models.Report).filter(models.Report.method_run_id == method_run_id).first()
    if not rep_exists:
        report = models.Report(
            id=f"rep_{uuid.uuid4().hex[:8]}",
            experiment_id=run.experiment_id,
            method_run_id=method_run_id,
            job_id=None,
            report_type="external",
            report_path=report_path,
            metrics_json=json.dumps(result_data.get("overall_metrics", {})),
            figures_json=json.dumps({}),
        )
        db.add(report)
    elif local_job_id and rep_exists.report_path == "external_method":
        rep_exists.report_path = report_path

    db.commit()
    return {"success": True}


@app.get("/api/v1/experiments/{experiment_id}/comparison")
async def get_comparison(experiment_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _owned_experiment(experiment_id, db, user)
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


@app.get("/api/v1/agent-report")
async def proxy_agent_report(local_job_id: str, session_token: str, agent_url: str = "http://127.0.0.1:17890"):
    """直接从 Agent 代理指定 local_job_id 的 HTML 报告，无需 DB report 记录。"""
    try:
        from fastapi.responses import Response
        resp = _requests.get(
            f"{agent_url}/api/v1/local/tasks/{local_job_id}/report",
            headers={"Authorization": f"Bearer {session_token}"},
            timeout=15,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Agent 报告未找到")
        return Response(content=resp.content, media_type="text/html")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"无法从 Agent 获取报告: {e}")


# ── Summary stats (for Dashboard) ────────────────────────────────────────────
@app.get("/api/v1/stats/summary")
async def get_summary(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    my_exp_ids = [e.id for e in db.query(models.Experiment.id).filter(models.Experiment.user_id == user.id).all()]
    runs_q = db.query(models.MethodRun).filter(models.MethodRun.experiment_id.in_(my_exp_ids)) if my_exp_ids else None
    return {
        "total_datasets": db.query(models.Dataset).filter(models.Dataset.user_id == user.id).count(),
        "total_experiments": len(my_exp_ids),
        "total_method_runs": runs_q.count() if runs_q else 0,
        "successful_runs": runs_q.filter(models.MethodRun.status == "success").count() if runs_q else 0,
        "total_reports": db.query(models.Report).filter(models.Report.experiment_id.in_(my_exp_ids)).count() if my_exp_ids else 0,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
