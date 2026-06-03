import os
import sys
import json
import logging
import time
from typing import Optional
import pandas as pd
import numpy as np

# Configure runner logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("evaluate-annotation")

def run_evaluation(
    adata_path: str,
    pred_csv_path: str,
    label_col: str,
    output_dir: str,
    match_mode: str = "relaxed",  # "strict" or "relaxed"
    cell_id_col: Optional[str] = None
):
    logger.info(f"Starting annotation evaluation. h5ad={adata_path}, prediction={pred_csv_path}")
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Read true labels from h5ad (obs_names and label_col)
    import anndata
    adata = anndata.read_h5ad(adata_path, backed='r')
    
    true_df = pd.DataFrame(index=adata.obs_names)
    true_df["true_label"] = adata.obs[label_col].astype(str).str.strip()
    
    # 2. Read prediction CSV
    pred_df = pd.read_csv(pred_csv_path)
    
    # Validation of required fields (10.1 Annotation Prediction CSV)
    if "cell_id" not in pred_df.columns or "pred_label" not in pred_df.columns:
        raise ValueError("Prediction CSV must contain 'cell_id' and 'pred_label' columns.")
        
    pred_df["cell_id"] = pred_df["cell_id"].astype(str).str.strip()
    pred_df["pred_label"] = pred_df["pred_label"].astype(str).str.strip()
    
    total_pred_cells = len(pred_df)
    
    # 3. Cell ID Matching Strategy (13. cell_id matching)
    # Check match rate
    merged = pd.merge(pred_df, true_df, left_on="cell_id", right_index=True, how="inner")
    matched_cells = len(merged)
    match_rate = matched_cells / total_pred_cells if total_pred_cells > 0 else 0.0
    
    logger.info(f"Cell ID match rate: {match_rate:.4f} ({matched_cells}/{total_pred_cells})")
    
    # 13.4 Match failure handling
    if match_rate < 0.95 and match_mode == "strict":
        raise ValueError(f"Cell ID match rate {match_rate:.2%} is below the 95% threshold in strict mode.")
    
    if matched_cells == 0:
        raise ValueError("Zero cells matched between prediction CSV and dataset.")
        
    # 4. Clean invalid labels (14.1 Label cleaning)
    invalid_labels = ["NaN", "None", "", "NA", "Unknown", "unknown", "unassigned", "Unassigned"]
    valid_mask = (~merged["true_label"].isin(invalid_labels)) & (merged["true_label"].notna())
    valid_merged = merged[valid_mask]
    
    valid_cells_count = len(valid_merged)
    logger.info(f"Valid cells for metrics computation: {valid_cells_count} (out of {matched_cells} matched)")
    
    if valid_cells_count == 0:
        raise ValueError("No valid ground-truth labels remaining after cleaning invalid values.")
        
    # 5. Compute metrics using scikit-learn
    from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support, confusion_matrix, balanced_accuracy_score
    
    y_true = valid_merged["true_label"].values
    y_pred = valid_merged["pred_label"].values
    
    # Fix potential class mismatch (14.3 Degeneracy cases)
    # If all predictions are the same, sklearn will handle it, but we can compute what we can
    accuracy = float(accuracy_score(y_true, y_pred))
    balanced_acc = float(balanced_accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro"))
    weighted_f1 = float(f1_score(y_true, y_pred, average="weighted"))
    
    # Per class metrics
    unique_classes = sorted(list(set(y_true) | set(y_pred)))
    precisions, recalls, f1s, supports = precision_recall_fscore_support(
        y_true, y_pred, labels=unique_classes, zero_division=0
    )
    
    per_class_metrics = {}
    for idx, cls_name in enumerate(unique_classes):
        per_class_metrics[cls_name] = {
            "precision": float(precisions[idx]),
            "recall": float(recalls[idx]),
            "f1": float(f1s[idx]),
            "support": int(supports[idx])
        }
        
    # Confusion Matrix
    cm = confusion_matrix(y_true, y_pred, labels=unique_classes)
    confusion_matrix_data = {
        "classes": unique_classes,
        "matrix": cm.tolist()
    }
    
    # Confidence calibration metrics if confidence column exists
    confidence_calibration = {}
    if "confidence" in valid_merged.columns:
        valid_merged["confidence"] = pd.to_numeric(valid_merged["confidence"], errors="coerce").fillna(0.0)
        # Simple ECE (Expected Calibration Error) or confidence distribution
        conf_values = valid_merged["confidence"].values
        correct_mask = (y_true == y_pred)
        confidence_calibration = {
            "mean_confidence": float(np.mean(conf_values)),
            "mean_confidence_correct": float(np.mean(conf_values[correct_mask])) if any(correct_mask) else 0.0,
            "mean_confidence_incorrect": float(np.mean(conf_values[~correct_mask])) if any(~correct_mask) else 0.0,
        }
    
    # 6. Save results to JSON (19.3 result.json)
    result = {
        "success": True,
        "task_type": "annotation_evaluation",
        "method_name": pred_df["method_name"].iloc[0] if "method_name" in pred_df.columns else "CustomMethod",
        "matching_summary": {
            "total_prediction_cells": total_pred_cells,
            "matched_cells": matched_cells,
            "match_rate": round(match_rate, 4),
            "valid_cells_count": valid_cells_count,
            "invalid_cells_count": matched_cells - valid_cells_count
        },
        "overall_metrics": {
            "accuracy": round(accuracy, 4),
            "balanced_accuracy": round(balanced_acc, 4),
            "macro_f1": round(macro_f1, 4),
            "weighted_f1": round(weighted_f1, 4)
        },
        "per_class_metrics": per_class_metrics,
        "confusion_matrix": confusion_matrix_data,
        "confidence_calibration": confidence_calibration,
        "timestamp": time.time()
    }
    
    result_path = os.path.join(output_dir, "result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)
        
    logger.info(f"Evaluation metrics written to {result_path}")
    return result

if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python evaluate_annotation.py <adata_path> <pred_csv> <label_col> <output_dir> <match_mode>")
        sys.exit(1)
        
    adata_path = sys.argv[1]
    pred_csv = sys.argv[2]
    label_col = sys.argv[3]
    output_dir = sys.argv[4]
    match_mode = sys.argv[5]
    
    try:
        run_evaluation(adata_path, pred_csv, label_col, output_dir, match_mode)
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        # Write error result
        with open(os.path.join(output_dir, "result.json"), "w", encoding="utf-8") as f:
            json.dump({"success": False, "error": str(e)}, f)
        sys.exit(1)
