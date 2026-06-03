import os
import json
import numpy as np
import pandas as pd

def initialize():
    # Setup directories
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workspace_dir = os.path.join(base_dir, "workspace")
    datasets_dir = os.path.join(workspace_dir, "datasets")
    predictions_dir = os.path.join(workspace_dir, "predictions", "imported_predictions")
    
    os.makedirs(datasets_dir, exist_ok=True)
    os.makedirs(predictions_dir, exist_ok=True)
    
    logger_path = os.path.join(workspace_dir, "init.log")
    print(f"Initializing scAnnoRare mock workspaces under: {workspace_dir}")
    
    # 1. Generate tiny_dataset.h5ad
    try:
        import anndata
        n_cells = 200
        n_genes = 1000
        
        # Random gene expression counts matrix
        X = np.random.poisson(lam=1.5, size=(n_cells, n_genes)).astype(np.float32)
        
        # Create cell labels (including standard and rare cells < 5% ratio)
        # Standard: B cell (80), T cell (75), Monocyte (35)
        # Rare: ASDC (4 cells, 2%), pDC (6 cells, 3%)
        labels = (
            ["B cell"] * 80 + 
            ["T cell"] * 75 + 
            ["Monocyte"] * 35 + 
            ["ASDC"] * 4 + 
            ["pDC"] * 6
        )
        # Random shuffle labels
        np.random.seed(42)
        np.random.shuffle(labels)
        
        # Batch column mock
        batches = np.random.choice(["Batch1", "Batch2"], size=n_cells).tolist()
        
        # AnnData creation
        obs = pd.DataFrame({
            "cell_type": labels,
            "batch": batches
        }, index=[f"cell_{i:03d}" for i in range(n_cells)])
        
        var = pd.DataFrame(index=[f"gene_{j:04d}" for j in range(n_genes)])
        
        adata = anndata.AnnData(X=X, obs=obs, var=var)
        adata_path = os.path.join(datasets_dir, "tiny_dataset.h5ad")
        
        # Write h5ad
        adata.write_h5ad(adata_path)
        print(f"Successfully generated: {adata_path}")
        
    except ImportError:
        print("Skipping h5ad generation because anndata/pandas packages are missing in this environment.")
        return

    # 2. Generate matching tiny_predictions.csv
    # In this prediction, MyRareMethod predicts mostly correctly, but makes a few mistakes 
    # and outputs continuous rare_score and prior baseline_label
    pred_labels = []
    baseline_labels = []
    rare_scores = []
    confidences = []
    
    for idx, true_lbl in enumerate(labels):
        cell_id = f"cell_{idx:03d}"
        
        # Add some noise to prediction labels
        # 90% accuracy overall
        rand = np.random.rand()
        if rand < 0.90:
            pred_lbl = true_lbl
        else:
            pred_lbl = np.random.choice(["B cell", "T cell", "Monocyte"])
            
        pred_labels.append(pred_lbl)
        
        # Mock baseline label (unrescued: baseline thought pDC/ASDC were Monocytes)
        if true_lbl in ["ASDC", "pDC"]:
            baseline_labels.append("Monocyte")
        else:
            baseline_labels.append(true_lbl)
            
        # Mock rare_score (higher for rare cells)
        if true_lbl in ["ASDC", "pDC"]:
            score = np.random.uniform(0.70, 0.98)
        else:
            score = np.random.uniform(0.01, 0.35)
        rare_scores.append(score)
        
        # Confidence
        conf = np.random.uniform(0.80, 0.99) if pred_lbl == true_lbl else np.random.uniform(0.40, 0.75)
        confidences.append(conf)
        
    pred_df = pd.DataFrame({
        "cell_id": [f"cell_{i:03d}" for i in range(n_cells)],
        "pred_label": pred_labels,
        "confidence": confidences,
        "is_pred_rare": [str(l in ["ASDC", "pDC"]).lower() for l in pred_labels],
        "rare_score": rare_scores,
        "baseline_label": baseline_labels,
        "method_name": "MyRareMethod"
    })
    
    csv_path = os.path.join(predictions_dir, "tiny_predictions.csv")
    pred_df.to_csv(csv_path, index=False)
    print(f"Successfully generated: {csv_path}")

if __name__ == "__main__":
    initialize()
