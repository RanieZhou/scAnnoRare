"""计算 2D UMAP 嵌入用于可视化。

输出 result.json:
  { success, n_points, n_total, subsampled, classes:[...],
    x:[...], y:[...], label:[...], pred:[...]?, correct:[...]? }

用法：
  python compute_embedding.py <adata_path> <label_col> <output_dir> [max_cells] [pred_csv]
"""
import os
import sys
import json
import logging
import warnings

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("compute-embedding")


def compute_embedding(adata_path, label_col, output_dir, max_cells=4000, pred_csv=None):
    import anndata
    import scanpy as sc
    import numpy as np
    import pandas as pd

    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"加载 {adata_path}")
    adata = anndata.read_h5ad(adata_path)
    n_total = adata.shape[0]

    # 子采样以保证响应速度
    subsampled = False
    if n_total > max_cells:
        idx = np.random.RandomState(0).choice(n_total, max_cells, replace=False)
        idx.sort()
        adata = adata[idx].copy()
        subsampled = True
        logger.info(f"子采样 {max_cells}/{n_total} 细胞")

    # 若已有嵌入直接用，否则标准流程计算
    if "X_umap" in adata.obsm:
        logger.info("使用数据集自带 X_umap")
        emb = adata.obsm["X_umap"]
    else:
        logger.info("计算 UMAP（normalize→log1p→PCA→neighbors→umap）")
        try:
            if float(adata.X.max()) > 30:
                sc.pp.normalize_total(adata, target_sum=1e4)
                sc.pp.log1p(adata)
        except Exception:
            pass
        sc.pp.highly_variable_genes(adata, n_top_genes=2000)
        adata = adata[:, adata.var.highly_variable].copy() if adata.var.get("highly_variable") is not None else adata
        sc.pp.scale(adata, max_value=10)
        sc.tl.pca(adata, n_comps=min(50, adata.shape[1] - 1))
        sc.pp.neighbors(adata, n_neighbors=15)
        sc.tl.umap(adata)
        emb = adata.obsm["X_umap"]

    x = [round(float(v), 3) for v in emb[:, 0]]
    y = [round(float(v), 3) for v in emb[:, 1]]
    true_labels = adata.obs[label_col].astype(str).str.strip().tolist()

    result = {
        "success": True,
        "task_type": "compute_embedding",
        "n_points": len(x),
        "n_total": n_total,
        "subsampled": subsampled,
        "x": x, "y": y, "label": true_labels,
        "classes": sorted(set(true_labels)),
    }

    # 可选：叠加预测 / 对错
    if pred_csv and os.path.exists(pred_csv):
        try:
            pred_df = pd.read_csv(pred_csv)
            pred_df["cell_id"] = pred_df["cell_id"].astype(str).str.strip()
            pmap = dict(zip(pred_df["cell_id"], pred_df["pred_label"].astype(str)))
            ids = adata.obs_names.astype(str)
            preds = [pmap.get(c, "NA") for c in ids]
            result["pred"] = preds
            result["correct"] = [int(p == t) for p, t in zip(preds, true_labels)]
        except Exception as e:
            logger.warning(f"预测叠加失败: {e}")

    with open(os.path.join(output_dir, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    logger.info(f"嵌入计算完成，{len(x)} 点")
    return result


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python compute_embedding.py <adata_path> <label_col> <output_dir> [max_cells] [pred_csv]")
        sys.exit(1)
    adata_path = sys.argv[1]
    label_col = sys.argv[2]
    output_dir = sys.argv[3]
    max_cells = int(sys.argv[4]) if len(sys.argv) > 4 else 4000
    pred_csv = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] not in ("", "None") else None
    try:
        compute_embedding(adata_path, label_col, output_dir, max_cells, pred_csv)
    except Exception as e:
        logger.error(f"嵌入计算失败: {e}")
        with open(os.path.join(output_dir, "result.json"), "w", encoding="utf-8") as f:
            json.dump({"success": False, "error": str(e)}, f)
        sys.exit(1)
