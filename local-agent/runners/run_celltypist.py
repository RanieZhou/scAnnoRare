"""内置方法运行：CellTypist 注释 → 复用现有 annotation 评估流水线。

用法（由用户选择的本地 Python 环境执行）：
  python run_celltypist.py <adata_path> <label_col> <output_dir> <model> <match_mode>
"""
import os
import sys
import json
import logging
import warnings

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("run-celltypist")


def run_celltypist(adata_path, label_col, output_dir,
                   model="Immune_All_Low.pkl", match_mode="relaxed"):
    import anndata
    import scanpy as sc
    import celltypist
    from celltypist import models
    import pandas as pd

    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"加载数据 {adata_path}")
    adata = anndata.read_h5ad(adata_path)  # 方法运行需完整表达矩阵，全量加载

    # 归一化：原始 counts（X 最大值偏大）则 normalize_total + log1p，否则视为已归一化
    work = adata.copy()
    try:
        xmax = float(work.X.max())
    except Exception:
        xmax = 1e9
    if xmax > 30:
        logger.info("检测为原始 counts，执行 normalize_total(1e4) + log1p")
        sc.pp.normalize_total(work, target_sum=1e4)
        sc.pp.log1p(work)

    logger.info(f"准备模型 {model}")
    models.download_models(model=model, force_update=False)

    logger.info("CellTypist 预测中…")
    pred = celltypist.annotate(work, model=model, majority_voting=False)
    labels = pred.predicted_labels
    pred_col = "predicted_labels" if "predicted_labels" in labels.columns else labels.columns[0]

    pred_df = pd.DataFrame({
        "cell_id": adata.obs_names.astype(str),
        "pred_label": labels[pred_col].astype(str).values,
    })
    # 置信度：取概率矩阵每行最大值
    try:
        prob = pred.probability_matrix
        pred_df["confidence"] = prob.max(axis=1).values
    except Exception:
        pass

    pred_csv = os.path.join(output_dir, "celltypist_predictions.csv")
    pred_df.to_csv(pred_csv, index=False)
    logger.info(f"预测结果写入 {pred_csv}（{len(pred_df)} 细胞）")

    # 复用现有注释评估流水线（cell_id 对齐 + 指标计算 + result.json）
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from evaluate_annotation import run_evaluation
    result = run_evaluation(adata_path, pred_csv, label_col, output_dir, match_mode)

    # 覆盖方法名为内置 CellTypist
    result["method_name"] = f"CellTypist:{model.replace('.pkl', '')}"
    result["builtin_method"] = "celltypist"
    result["builtin_model"] = model
    with open(os.path.join(output_dir, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    logger.info("CellTypist 内置运行完成")
    return result


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python run_celltypist.py <adata_path> <label_col> <output_dir> [model] [match_mode]")
        sys.exit(1)
    adata_path = sys.argv[1]
    label_col = sys.argv[2]
    output_dir = sys.argv[3]
    model = sys.argv[4] if len(sys.argv) > 4 else "Immune_All_Low.pkl"
    match_mode = sys.argv[5] if len(sys.argv) > 5 else "relaxed"
    try:
        run_celltypist(adata_path, label_col, output_dir, model, match_mode)
    except Exception as e:
        logger.error(f"CellTypist 运行失败: {e}")
        with open(os.path.join(output_dir, "result.json"), "w", encoding="utf-8") as f:
            json.dump({"success": False, "error": str(e)}, f)
        sys.exit(1)
