import time
from sqlalchemy import Column, String, Integer, Float, ForeignKey, Text
from app.db import Base


class User(Base):
    __tablename__ = "users"
    id            = Column(String(50),  primary_key=True, index=True)
    email         = Column(String(100), unique=True, index=True)
    username      = Column(String(50),  unique=True, index=True)
    password_hash = Column(String(200))
    token         = Column(String(64),  unique=True, index=True, nullable=True)
    created_at    = Column(Float, default=time.time)
    updated_at    = Column(Float, default=time.time)


class Project(Base):
    __tablename__ = "projects"
    id           = Column(String(50),  primary_key=True, index=True)
    user_id      = Column(String(50),  ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    project_name = Column(String(100), index=True)
    description  = Column(Text, nullable=True)
    created_at   = Column(Float, default=time.time)
    updated_at   = Column(Float, default=time.time)


class Dataset(Base):
    __tablename__ = "datasets"
    id                    = Column(String(50),  primary_key=True, index=True)
    project_id            = Column(String(50),  ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    dataset_name          = Column(String(100), index=True)
    local_dataset_alias   = Column(String(500))
    label_col             = Column(String(100), nullable=True)
    batch_col             = Column(String(100), nullable=True)
    n_cells               = Column(Integer)
    n_genes               = Column(Integer)
    obs_columns_json      = Column(Text)
    var_columns_json      = Column(Text)
    label_distribution_json = Column(Text)
    rare_candidates_json  = Column(Text)
    created_at            = Column(Float, default=time.time)
    updated_at            = Column(Float, default=time.time)


class Agent(Base):
    __tablename__ = "agents"
    id                  = Column(String(50),  primary_key=True, index=True)
    user_id             = Column(String(50),  ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    agent_name          = Column(String(100))
    device_id           = Column(String(100), unique=True)
    os                  = Column(String(100))
    cpu_summary_json    = Column(Text)
    gpu_summary_json    = Column(Text)
    package_summary_json = Column(Text)
    last_seen_at        = Column(Float, default=time.time)
    status              = Column(String(20))
    created_at          = Column(Float, default=time.time)
    updated_at          = Column(Float, default=time.time)


class Experiment(Base):
    __tablename__ = "experiments"
    id                      = Column(String(50),  primary_key=True, index=True)
    project_id              = Column(String(50),  ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    dataset_id              = Column(String(50),  ForeignKey("datasets.id", ondelete="CASCADE"))
    experiment_name         = Column(String(100), index=True)
    task_type               = Column(String(50))
    label_col               = Column(String(100))
    batch_col               = Column(String(100), nullable=True)
    rare_mode               = Column(String(50),  nullable=True)
    rare_threshold          = Column(Float, nullable=True)
    target_rare_classes_json = Column(Text, nullable=True)
    split_config_json       = Column(Text, nullable=True)
    evaluation_config_json  = Column(Text, nullable=True)
    created_at              = Column(Float, default=time.time)
    updated_at              = Column(Float, default=time.time)


class MethodRun(Base):
    __tablename__ = "method_runs"
    id                    = Column(String(50),  primary_key=True, index=True)
    experiment_id         = Column(String(50),  ForeignKey("experiments.id", ondelete="CASCADE"))
    method_name           = Column(String(100), index=True)
    method_type           = Column(String(50))
    input_type            = Column(String(50))
    prediction_file_alias = Column(String(500))
    baseline_file_alias   = Column(String(500), nullable=True)
    config_json           = Column(Text, nullable=True)
    status                = Column(String(20))
    created_at            = Column(Float, default=time.time)
    updated_at            = Column(Float, default=time.time)


class Job(Base):
    __tablename__ = "jobs"
    id                 = Column(String(50),  primary_key=True, index=True)
    experiment_id      = Column(String(50),  ForeignKey("experiments.id", ondelete="CASCADE"))
    method_run_id      = Column(String(50),  ForeignKey("method_runs.id", ondelete="CASCADE"))
    agent_id           = Column(String(50),  nullable=True)        # soft ref, no FK constraint
    job_type           = Column(String(50))
    status             = Column(String(20))
    progress           = Column(Integer, default=0)
    local_job_id       = Column(String(50),  nullable=True)
    config_json        = Column(Text, nullable=True)
    result_summary_json = Column(Text, nullable=True)
    created_at         = Column(Float, default=time.time)
    started_at         = Column(Float, nullable=True)
    finished_at        = Column(Float, nullable=True)


class MethodResult(Base):
    __tablename__ = "method_results"
    id                    = Column(String(50), primary_key=True, index=True)
    method_run_id         = Column(String(50), ForeignKey("method_runs.id", ondelete="CASCADE"))
    job_id                = Column(String(50), ForeignKey("jobs.id",        ondelete="CASCADE"))
    metrics_json          = Column(Text)
    per_class_metrics_json = Column(Text)
    rare_metrics_json     = Column(Text, nullable=True)
    confusion_matrix_json = Column(Text)
    curve_data_json       = Column(Text, nullable=True)
    figures_json          = Column(Text, nullable=True)
    created_at            = Column(Float, default=time.time)


class Report(Base):
    __tablename__ = "reports"
    id             = Column(String(50), primary_key=True, index=True)
    experiment_id  = Column(String(50), ForeignKey("experiments.id",  ondelete="CASCADE"))
    method_run_id  = Column(String(50), ForeignKey("method_runs.id",  ondelete="CASCADE"))
    job_id         = Column(String(50), ForeignKey("jobs.id",         ondelete="CASCADE"))
    report_type    = Column(String(20))
    report_path    = Column(String(500))
    metrics_json   = Column(Text)
    figures_json   = Column(Text)
    created_at     = Column(Float, default=time.time)
