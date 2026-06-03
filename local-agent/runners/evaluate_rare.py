import os
import sys
import json
import logging
import time
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

# Configure runner logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("evaluate-rare")

def compute_binary_metrics(y_true_bin, y_pred_bin, rare_scores=None):
    """
    Compute binary classification metrics for rare cell detection.
    """
    from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, roc_auc_score, precision_recall_curve, auc
    
    # Threshold metrics
    precision = float(precision_score(y_true_bin, y_pred_bin, zero_division=0))
    recall = float(recall_score(y_true_bin, y_pred_bin, zero_division=0))
    f1 = float(f1_score(y_true_bin, y_pred_bin, zero_division=0))
    
    cm = confusion_matrix(y_true_bin, y_pred_bin)
    # Handle potentially single-class confusion matrix
    tn, fp, fn, tp = 0, 0, 0, 0
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
    elif cm.shape == (1, 1):
        # Only one class present in prediction/truth
        val = y_true_bin[0] if len(y_true_bin) > 0 else 0
        if val == 1:
            tp = len(y_true_bin)
        else:
            tn = len(y_true_bin)
            
    false_positive_count = int(fp)
    false_negative_count = int(fn)
    missed_rare_count = int(fn)
    
    metrics = {
        "rare_precision": round(precision, 4),
        "rare_recall": round(recall, 4),
        "rare_f1": round(f1, 4),
        "false_positive_count": false_positive_count,
        "false_negative_count": false_negative_count,
        "missed_rare_count": missed_rare_count,
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp)
        }
    }
    
    # 11.3 Curve metrics if rare_score exists
    if rare_scores is not None and len(np.unique(y_true_bin)) > 1:
        try:
            auroc = float(roc_auc_score(y_true_bin, rare_scores))
            
            # PR Curve and AUPRC (Average Precision / AUC of PR)
            precision_pts, recall_pts, _ = precision_recall_curve(y_true_bin, rare_scores)
            auprc = float(auc(recall_pts, precision_pts))
            
            # ROC points for visualization
            from sklearn.metrics import roc_curve
            fpr_pts, tpr_pts, _ = roc_curve(y_true_bin, rare_scores)
            
            # Downsample curve points for smaller transfer size in JSON (e.g., max 100 points)
            step_roc = max(1, len(fpr_pts) // 100)
            step_pr = max(1, len(precision_pts) // 100)
            
            metrics["auroc"] = round(auroc, 4)
            metrics["auprc"] = round(auprc, 4)
            metrics["roc_curve"] = {
                "fpr": fpr_pts[::step_roc].tolist(),
                "tpr": tpr_pts[::step_roc].tolist()
            }
            metrics["pr_curve"] = {
                "precision": precision_pts[::step_pr].tolist(),
                "recall": recall_pts[::step_pr].tolist()
            }
        except Exception as e:
            logger.warning(f"Failed to calculate curve metrics: {e}")
            metrics["auroc"] = None
            metrics["auprc"] = None
    else:
        metrics["auroc"] = None
        metrics["auprc"] = None
        
    return metrics

def run_rare_evaluation(
    adata_path: str,
    pred_csv_path: str,
    label_col: str,
    output_dir: str,
    rare_mode: str,
    target_rare_classes: List[str],
    match_mode: str = "relaxed",
    cell_id_col: Optional[str] = None
):
    logger.info(f"Starting rare detection evaluation. mode={rare_mode}, targets={target_rare_classes}")
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Read true labels from h5ad
    import anndata
    adata = anndata.read_h5ad(adata_path, backed='r')
    
    true_df = pd.DataFrame(index=adata.obs_names)
    true_df["true_label"] = adata.obs[label_col].astype(str).str.strip()
    
    # 2. Read prediction CSV
    pred_df = pd.read_csv(pred_csv_path)
    
    if "cell_id" not in pred_df.columns:
        raise ValueError("Prediction CSV must contain a 'cell_id' column.")
        
    pred_df["cell_id"] = pred_df["cell_id"].astype(str).str.strip()
    
    total_pred_cells = len(pred_df)
    
    # Merge for Cell ID Match (13. cell_id matching)
    merged = pd.merge(pred_df, true_df, left_on="cell_id", right_index=True, how="inner")
    matched_cells = len(merged)
    match_rate = matched_cells / total_pred_cells if total_pred_cells > 0 else 0.0
    
    if match_rate < 0.95 and match_mode == "strict":
        raise ValueError(f"Cell ID match rate {match_rate:.2%} is below strict threshold 95%.")
        
    if matched_cells == 0:
        raise ValueError("Zero cells matched between prediction CSV and dataset.")

    # 14.1 Clean invalid labels
    invalid_labels = ["NaN", "None", "", "NA", "Unknown", "unknown", "unassigned", "Unassigned"]
    valid_mask = (~merged["true_label"].isin(invalid_labels)) & (merged["true_label"].notna())
    valid_merged = merged[valid_mask].copy()
    
    if len(valid_merged) == 0:
        raise ValueError("No cells with valid true labels to compute metrics.")

    # Ensure pred_label or is_pred_rare columns exist
    # 10.2: Rare Detection Prediction CSV requires cell_id. is_pred_rare or pred_label is used to determine binary prediction.
    if "is_pred_rare" in valid_merged.columns:
        # Convert true/false strings or booleans
        valid_merged["is_pred_rare_bool"] = valid_merged["is_pred_rare"].astype(str).str.lower().isin(["true", "1", "yes", "rare"])
    elif "pred_label" in valid_merged.columns:
        # If true_label in target_rare_classes, is it predicted as one of them?
        valid_merged["is_pred_rare_bool"] = valid_merged["pred_label"].isin(target_rare_classes)
    else:
        raise ValueError("Prediction CSV must contain either 'is_pred_rare' or 'pred_label' column.")

    # Extract score if available
    rare_scores = None
    if "rare_score" in valid_merged.columns:
        rare_scores = pd.to_numeric(valid_merged["rare_score"], errors="coerce").fillna(0.0).values

    # Determine True Rare binary arrays based on rare_mode (12. Rare Mode)
    results = {}
    
    if rare_mode == "single_rare":
        r = target_rare_classes[0]
        y_true_bin = (valid_merged["true_label"] == r).astype(int).values
        y_pred_bin = valid_merged["is_pred_rare_bool"].astype(int).values
        
        results["overall_metrics"] = compute_binary_metrics(y_true_bin, y_pred_bin, rare_scores)
        results["mode_info"] = {"mode": "single_rare", "target": r}
        
    elif rare_mode == "pooled_rare_vs_nonrare":
        y_true_bin = valid_merged["true_label"].isin(target_rare_classes).astype(int).values
        y_pred_bin = valid_merged["is_pred_rare_bool"].astype(int).values
        
        results["overall_metrics"] = compute_binary_metrics(y_true_bin, y_pred_bin, rare_scores)
        results["mode_info"] = {"mode": "pooled_rare_vs_nonrare", "targets": target_rare_classes}
        
    elif rare_mode == "multi_rare_per_class":
        # Per class one-vs-rest metrics
        class_metrics = {}
        for r in target_rare_classes:
            y_true_bin_r = (valid_merged["true_label"] == r).astype(int).values
            
            # Predict as rare specifically for class r?
            if "pred_label" in valid_merged.columns:
                y_pred_bin_r = (valid_merged["pred_label"] == r).astype(int).values
            else:
                y_pred_bin_r = valid_merged["is_pred_rare_bool"].astype(int).values
                
            class_metrics[r] = compute_binary_metrics(y_true_bin_r, y_pred_bin_r, rare_scores)
            
        results["per_class_metrics"] = class_metrics
        # Overall aggregate of per class F1
        f1s = [m["rare_f1"] for m in class_metrics.values() if m["rare_f1"] is not None]
        recalls = [m["rare_recall"] for m in class_metrics.values() if m["rare_recall"] is not None]
        
        results["overall_metrics"] = {
            "macro_rare_f1": round(float(np.mean(f1s)), 4) if f1s else 0.0,
            "macro_rare_recall": round(float(np.mean(recalls)), 4) if recalls else 0.0
        }
        results["mode_info"] = {"mode": "multi_rare_per_class", "targets": target_rare_classes}

    # 11.4 False Rescue Rate (FRR) calculation
    # Only if baseline_label or decision_type column exists
    frr_data = {}
    if "baseline_label" in valid_merged.columns or "decision_type" in valid_merged.columns:
        # Determine baseline_label
        if "baseline_label" not in valid_merged.columns:
            # Reconstruct from decision_type if needed, or default
            valid_merged["baseline_label"] = valid_merged["true_label"]  # fallback
            
        valid_merged["baseline_label"] = valid_merged["baseline_label"].astype(str).str.strip()
        
        # Calculate FRR for each rare class r
        frr_by_class = {}
        for r in target_rare_classes:
            # rescue attempt: baseline != r and pred == r (or pred is rare)
            # In multi_rare_per_class, we check specific pred_label == r. In other modes, we check predicted as rare.
            if "pred_label" in valid_merged.columns:
                pred_is_r = (valid_merged["pred_label"] == r)
            else:
                pred_is_r = valid_merged["is_pred_rare_bool"]
                
            rescue_attempt_mask = (valid_merged["baseline_label"] != r) & pred_is_r
            rescue_attempt_count = int(np.sum(rescue_attempt_mask))
            
            # false rescue: true_label != r and baseline_label != r and pred_label == r
            false_rescue_mask = (valid_merged["true_label"] != r) & rescue_attempt_mask
            false_rescue_count = int(np.sum(false_rescue_mask))
            
            frr = float(false_rescue_count / max(rescue_attempt_count, 1))
            frr_by_class[r] = {
                "rescue_attempt_count": rescue_attempt_count,
                "false_rescue_count": false_rescue_count,
                "false_rescue_rate": round(frr, 4)
            }
        results["false_rescue_rate"] = frr_by_class
    else:
        results["false_rescue_rate"] = None

    # Save results (19.3 result.json)
    results["success"] = True
    results["task_type"] = "rare_detection_evaluation"
    results["matching_summary"] = {
        "total_prediction_cells": total_pred_cells,
        "matched_cells": matched_cells,
        "match_rate": round(match_rate, 4),
        "valid_cells_count": len(valid_merged)
    }
    
    result_path = os.path.join(output_dir, "result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
        
    logger.info(f"Rare cell metrics written to {result_path}")
    return results

if __name__ == "__main__":
    if len(sys.argv) < 7:
        print("Usage: python evaluate_rare.py <adata_path> <pred_csv> <label_col> <output_dir> <rare_mode> <target_rare_classes_json> <match_mode>")
        sys.exit(1)
        
    adata_path = sys.argv[1]
    pred_csv = sys.argv[2]
    label_col = sys.argv[3]
    output_dir = sys.argv[4]
    rare_mode = sys.argv[5]
    targets = json.loads(sys.argv[6])
    match_mode = sys.argv[7]
    
    try:
        run_rare_evaluation(adata_path, pred_csv, label_col, output_dir, rare_mode, targets, match_mode)
    except Exception as e:
        logger.error(f"Rare execution failed: {e}")
        with open(os.path.join(output_dir, "result.json"), "w", encoding="utf-8") as f:
            json.dump({"success": False, "error": str(e)}, f)
        sys.exit(1)
