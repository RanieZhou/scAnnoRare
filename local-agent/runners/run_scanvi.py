#!/usr/bin/env python3
"""
run_scanvi.py — scANVI cell-type annotation runner

Uses scvi-tools SCANVI (semi-supervised VAE) for cell type annotation.
Runs an 80/20 stratified train/test split: trains on labeled 80%,
predicts held-out 20%, outputs a prediction CSV compatible with
evaluate_annotation.py.

CLI usage:
    python run_scanvi.py <adata_path> <label_col> <output_dir>
                         [train_frac=0.8] [max_epochs=100] [match_mode=relaxed] [batch_col=None]
"""
import os
import sys
import json
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("run-scanvi")


def _best_accelerator() -> str:
    try:
        import torch
        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "gpu"
    except Exception:
        pass
    return "cpu"


def run_scanvi(
    adata_path: str,
    label_col: str,
    output_dir: str,
    train_frac: float = 0.8,
    max_epochs: int = 100,
    match_mode: str = "relaxed",
    batch_col: str = None,
):
    os.makedirs(output_dir, exist_ok=True)

    import numpy as np
    import pandas as pd
    import anndata
    import scvi

    logger.info(f"Loading dataset: {adata_path}")
    adata = anndata.read_h5ad(adata_path)

    # Filter invalid labels
    invalid = {"NaN", "None", "", "NA", "Unknown", "unknown", "unassigned", "Unassigned"}
    labels_raw = adata.obs[label_col].astype(str).str.strip()
    valid_mask = ~labels_raw.isin(invalid) & labels_raw.notna()
    adata = adata[valid_mask].copy()
    logger.info(f"Valid cells after label filter: {adata.n_obs}")

    # Ensure raw count matrix (scvi expects counts or at least non-negative values)
    # If .raw exists and looks like counts, use it; otherwise use .X as-is
    if adata.raw is not None:
        import scipy.sparse as sp
        raw_X = adata.raw.X
        if sp.issparse(raw_X):
            raw_X = raw_X.toarray()
        if raw_X.min() >= 0 and np.abs(raw_X - np.round(raw_X)).max() < 0.01:
            adata.X = adata.raw.X

    # Setup batch key: use provided batch_col or create dummy
    if batch_col and batch_col in adata.obs.columns:
        batch_key = batch_col
    else:
        adata.obs["_dummy_batch"] = "batch0"
        batch_key = "_dummy_batch"

    # Stratified 80/20 train/test split
    from sklearn.model_selection import train_test_split
    all_idx = np.arange(adata.n_obs)
    labels = adata.obs[label_col].astype(str).values
    try:
        train_idx, test_idx = train_test_split(
            all_idx, test_size=1 - train_frac, stratify=labels, random_state=42
        )
    except ValueError:
        logger.warning("Stratified split failed (some classes < 2 samples), using random split")
        train_idx, test_idx = train_test_split(all_idx, test_size=1 - train_frac, random_state=42)

    logger.info(f"Train: {len(train_idx)}  Test: {len(test_idx)}")

    # Build combined adata with "Unknown" label for test cells
    adata_train = adata[train_idx].copy()
    adata_test  = adata[test_idx].copy()

    adata_train.obs["_scanvi_label"] = adata_train.obs[label_col].astype(str)
    adata_test.obs["_scanvi_label"]  = "Unknown"

    import anndata as ad
    adata_combined = ad.concat(
        [adata_train, adata_test],
        label="_split", keys=["train", "test"],
        merge="same",
    )
    # Restore batch info
    if batch_key != "_dummy_batch":
        adata_combined.obs[batch_key] = pd.concat([
            adata_train.obs[batch_key], adata_test.obs[batch_key]
        ])
    else:
        adata_combined.obs["_dummy_batch"] = "batch0"

    adata_combined.obs["_scanvi_label"] = pd.concat([
        adata_train.obs["_scanvi_label"],
        adata_test.obs["_scanvi_label"],
    ])

    # Step 1: Train SCVI (unsupervised VAE)
    logger.info("Setting up SCVI model...")
    scvi.model.SCVI.setup_anndata(
        adata_combined,
        batch_key=batch_key,
        labels_key="_scanvi_label",
    )
    vae = scvi.model.SCVI(adata_combined, n_layers=2, n_latent=30, gene_likelihood="nb")
    logger.info(f"Training SCVI (max_epochs={max_epochs})...")
    accel = _best_accelerator()
    logger.info(f"Using accelerator: {accel}")
    vae.train(max_epochs=max_epochs, accelerator=accel, plan_kwargs={"lr": 1e-3}, enable_progress_bar=False)

    # Step 2: Train SCANVI (semi-supervised on top of SCVI)
    logger.info("Training SCANVI (semi-supervised)...")
    scanvi_epochs = max(20, max_epochs // 2)
    scanvi = scvi.model.SCANVI.from_scvi_model(
        vae,
        labels_key="_scanvi_label",
        unlabeled_category="Unknown",
    )
    scanvi.train(max_epochs=scanvi_epochs, accelerator=accel, enable_progress_bar=False)

    # Step 3: Predict labels for all cells (test cells get predicted, train get re-predicted)
    predictions = scanvi.predict()
    adata_combined.obs["_scanvi_pred"] = predictions

    # Extract test cell predictions
    test_obs = adata_combined.obs[adata_combined.obs["_split"] == "test"]

    # Build prediction CSV (cell_id, pred_label, method_name)
    true_labels_test = adata[test_idx].obs[label_col].astype(str).values
    pred_df = pd.DataFrame({
        "cell_id": test_obs.index.tolist(),
        "pred_label": test_obs["_scanvi_pred"].tolist(),
        "true_label_ref": true_labels_test,
        "method_name": f"scANVI (train={train_frac})",
    })

    pred_csv = os.path.join(output_dir, "scanvi_predictions.csv")
    pred_df.to_csv(pred_csv, index=False)
    logger.info(f"Predictions written: {pred_csv}  ({len(pred_df)} cells)")

    # Write a summary for the orchestrator
    summary = {
        "success": True,
        "pred_csv": pred_csv,
        "n_train": int(len(train_idx)),
        "n_test": int(len(test_idx)),
        "method_name": f"scANVI (train={train_frac})",
    }
    with open(os.path.join(output_dir, "scanvi_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    logger.info("scANVI prediction complete.")
    return pred_csv


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python run_scanvi.py <adata_path> <label_col> <output_dir> "
              "[train_frac] [max_epochs] [match_mode] [batch_col]")
        sys.exit(1)

    _adata_path  = sys.argv[1]
    _label_col   = sys.argv[2]
    _output_dir  = sys.argv[3]
    _train_frac  = float(sys.argv[4]) if len(sys.argv) > 4 else 0.8
    _max_epochs  = int(sys.argv[5])   if len(sys.argv) > 5 else 100
    _match_mode  = sys.argv[6]        if len(sys.argv) > 6 else "relaxed"
    _batch_col   = sys.argv[7] if len(sys.argv) > 7 and sys.argv[7] != "None" else None

    try:
        run_scanvi(
            adata_path=_adata_path,
            label_col=_label_col,
            output_dir=_output_dir,
            train_frac=_train_frac,
            max_epochs=_max_epochs,
            match_mode=_match_mode,
            batch_col=_batch_col,
        )
    except Exception as e:
        logger.error(f"scANVI run failed: {e}")
        import traceback
        traceback.print_exc()
        # Write failure marker so orchestrator knows
        try:
            with open(os.path.join(_output_dir, "scanvi_summary.json"), "w") as f:
                json.dump({"success": False, "error": str(e)}, f)
        except Exception:
            pass
        sys.exit(1)
