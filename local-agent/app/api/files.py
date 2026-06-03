import os
import json
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

logger = logging.getLogger("local-agent.files")
router = APIRouter()

# Schema definitions
class FileSelectRequest(BaseModel):
    filepath: str

class DatasetRegisterRequest(BaseModel):
    filepath: str
    dataset_name: str
    label_col: str
    batch_col: Optional[str] = None
    rare_threshold: Optional[float] = 0.05  # default 5%

# Helper to check if file is anndata
def is_h5ad_file(path: str) -> bool:
    if not os.path.exists(path):
        return False
    if not path.endswith(".h5ad"):
        return False
    return True

@router.post("/files/select")
async def select_file(payload: FileSelectRequest):
    """
    Simulate file selection or validate a given file path.
    For local agent, we directly test if the file is readable by anndata.
    """
    path = payload.filepath
    if not os.path.exists(path):
        raise HTTPException(status_code=400, detail="File path does not exist.")
    if not is_h5ad_file(path):
        raise HTTPException(status_code=400, detail="File is not a valid .h5ad file.")
    
    try:
        import anndata
        # read_h5ad with backed='r' is extremely fast and light
        adata = anndata.read_h5ad(path, backed='r')
        n_cells, n_genes = adata.shape
        obs_cols = list(adata.obs.columns)
        var_cols = list(adata.var.columns)
        
        # Close connection if supported in backed mode (done automatically in modern anndata)
        return {
            "success": True,
            "filepath": path,
            "n_cells": n_cells,
            "n_genes": n_genes,
            "obs_columns": obs_cols,
            "var_columns": var_cols
        }
    except Exception as e:
        logger.error(f"Error parsing h5ad file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse .h5ad file: {str(e)}")

@router.post("/files/register-dataset")
async def register_dataset(payload: DatasetRegisterRequest):
    """
    Inspect label/batch distribution and find rare candidates.
    """
    path = payload.filepath
    if not is_h5ad_file(path):
        raise HTTPException(status_code=400, detail="Invalid .h5ad file path.")
    
    try:
        import anndata
        import pandas as pd
        
        adata = anndata.read_h5ad(path, backed='r')
        
        # 24.2 Parameter validation: label_col must be in obs
        if payload.label_col not in adata.obs.columns:
            raise HTTPException(status_code=400, detail=f"label_col '{payload.label_col}' not found in dataset obs columns.")
            
        if payload.batch_col and payload.batch_col not in adata.obs.columns:
            raise HTTPException(status_code=400, detail=f"batch_col '{payload.batch_col}' not found in dataset obs columns.")

        # Read specific columns from obs to avoid loading entire object
        obs_df = pd.DataFrame(adata.obs[[payload.label_col]])
        if payload.batch_col:
            obs_df[payload.batch_col] = adata.obs[payload.batch_col]
            
        # Label distribution
        # Handle NaN/missing labels (14.1 Missing or invalid labels)
        invalid_labels = ["NaN", "None", "", "NA", "Unknown", "unknown", "unassigned", "Unassigned"]
        
        # Convert to string and strip
        obs_df[payload.label_col] = obs_df[payload.label_col].astype(str).str.strip()
        
        total_cells = len(obs_df)
        valid_mask = ~obs_df[payload.label_col].isin(invalid_labels) & obs_df[payload.label_col].notna()
        valid_df = obs_df[valid_mask]
        
        valid_label_cells = len(valid_df)
        invalid_label_cells = total_cells - valid_label_cells
        invalid_label_ratio = round(invalid_label_cells / total_cells if total_cells > 0 else 0, 4)
        
        label_counts = valid_df[payload.label_col].value_counts()
        label_distribution = {}
        rare_candidates = []
        
        for lbl, cnt in label_counts.items():
            ratio = float(cnt / valid_label_cells) if valid_label_cells > 0 else 0.0
            label_distribution[lbl] = {
                "count": int(cnt),
                "ratio": round(ratio, 4)
            }
            # If ratio is below threshold, it's a rare cell type candidate
            if ratio < payload.rare_threshold:
                rare_candidates.append({
                    "class_name": lbl,
                    "count": int(cnt),
                    "ratio": round(ratio, 4)
                })

        # Batch distribution if provided
        batch_distribution = {}
        if payload.batch_col:
            batch_counts = obs_df[payload.batch_col].value_counts()
            for b_lbl, b_cnt in batch_counts.items():
                batch_distribution[b_lbl] = {
                    "count": int(b_cnt),
                    "ratio": round(float(b_cnt / total_cells), 4)
                }

        # Save registration info locally in a JSON file registry (19.4 Local workspace)
        workspace_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "workspace")
        os.makedirs(workspace_dir, exist_ok=True)
        datasets_dir = os.path.join(workspace_dir, "datasets")
        os.makedirs(datasets_dir, exist_ok=True)
        
        registry_path = os.path.join(datasets_dir, "dataset_registry.json")
        registry = {}
        if os.path.exists(registry_path):
            try:
                with open(registry_path, "r", encoding="utf-8") as f:
                    registry = json.load(f)
            except Exception:
                pass
                
        registry[payload.dataset_name] = {
            "dataset_name": payload.dataset_name,
            "filepath": path,
            "n_cells": int(adata.shape[0]),
            "n_genes": int(adata.shape[1]),
            "label_col": payload.label_col,
            "batch_col": payload.batch_col,
            "total_cells": total_cells,
            "valid_label_cells": valid_label_cells,
            "invalid_label_cells": invalid_label_cells,
            "invalid_label_ratio": invalid_label_ratio,
            "label_distribution": label_distribution,
            "rare_candidates": rare_candidates,
            "batch_distribution": batch_distribution
        }
        
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=4, ensure_ascii=False)

        return {
            "success": True,
            "dataset_name": payload.dataset_name,
            "summary": registry[payload.dataset_name]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to register dataset: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze dataset obs: {str(e)}")
