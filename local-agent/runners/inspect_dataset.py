import json
import os
import sys


INVALID_LABELS = {"NaN", "None", "", "NA", "Unknown", "unknown", "unassigned", "Unassigned"}


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)


def select_file(filepath):
    import anndata

    adata = anndata.read_h5ad(filepath, backed="r")
    return {
        "success": True,
        "filepath": filepath,
        "n_cells": int(adata.shape[0]),
        "n_genes": int(adata.shape[1]),
        "obs_columns": [str(c) for c in adata.obs.columns],
        "var_columns": [str(c) for c in adata.var.columns],
    }


def register_dataset(filepath, dataset_name, label_col, batch_col, rare_threshold):
    import anndata
    import pandas as pd

    adata = anndata.read_h5ad(filepath, backed="r")
    if label_col not in adata.obs.columns:
        raise ValueError(f"label_col '{label_col}' not found in dataset obs columns.")
    if batch_col and batch_col != "None" and batch_col not in adata.obs.columns:
        raise ValueError(f"batch_col '{batch_col}' not found in dataset obs columns.")

    obs_df = pd.DataFrame(adata.obs[[label_col]])
    if batch_col and batch_col != "None":
        obs_df[batch_col] = adata.obs[batch_col]
    else:
        batch_col = None

    obs_df[label_col] = obs_df[label_col].astype(str).str.strip()
    total_cells = int(len(obs_df))
    valid_mask = ~obs_df[label_col].isin(INVALID_LABELS) & obs_df[label_col].notna()
    valid_df = obs_df[valid_mask]
    valid_label_cells = int(len(valid_df))
    invalid_label_cells = int(total_cells - valid_label_cells)
    invalid_label_ratio = round(invalid_label_cells / total_cells if total_cells else 0, 4)

    label_distribution = {}
    rare_candidates = []
    for lbl, cnt in valid_df[label_col].value_counts().items():
        label = str(lbl)
        count = int(cnt)
        ratio = float(count / valid_label_cells) if valid_label_cells else 0.0
        item = {"count": count, "ratio": round(ratio, 4)}
        label_distribution[label] = item
        if ratio < rare_threshold:
            rare_candidates.append({"class_name": label, **item})

    batch_distribution = {}
    if batch_col:
        for batch, cnt in obs_df[batch_col].value_counts().items():
            count = int(cnt)
            batch_distribution[str(batch)] = {
                "count": count,
                "ratio": round(float(count / total_cells), 4) if total_cells else 0,
            }

    return {
        "success": True,
        "dataset_name": dataset_name,
        "filepath": filepath,
        "n_cells": int(adata.shape[0]),
        "n_genes": int(adata.shape[1]),
        "label_col": label_col,
        "batch_col": batch_col,
        "total_cells": total_cells,
        "valid_label_cells": valid_label_cells,
        "invalid_label_cells": invalid_label_cells,
        "invalid_label_ratio": invalid_label_ratio,
        "label_distribution": label_distribution,
        "rare_candidates": rare_candidates,
        "batch_distribution": batch_distribution,
    }


def main():
    if len(sys.argv) < 4:
        print("Usage: python inspect_dataset.py <select|register> <output_json> <filepath> [...]", file=sys.stderr)
        sys.exit(2)

    mode = sys.argv[1]
    output_json = sys.argv[2]
    filepath = sys.argv[3]

    try:
        if mode == "select":
            result = select_file(filepath)
        elif mode == "register":
            if len(sys.argv) < 8:
                raise ValueError("register requires: filepath dataset_name label_col batch_col rare_threshold")
            result = register_dataset(
                filepath=filepath,
                dataset_name=sys.argv[4],
                label_col=sys.argv[5],
                batch_col=sys.argv[6],
                rare_threshold=float(sys.argv[7]),
            )
        else:
            raise ValueError(f"Unsupported mode: {mode}")
        write_json(output_json, result)
    except Exception as e:
        write_json(output_json, {"success": False, "error": str(e)})
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
