import os
import sys
import json
import logging
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from jinja2 import Template
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("generate-report")

# Beautiful retro-modern design CSS & HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>scAnnoRare 评估报告 - {{ method_name }}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Noto+Sans+SC:wght@300;400;700&display=swap');
        
        :root {
            --bg-color: #0d0f12;
            --card-bg: rgba(22, 28, 36, 0.7);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --primary: #6366f1;
            --primary-gradient: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
            --accent-green: #10b981;
            --accent-red: #ef4444;
        }
        
        body {
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: 'Outfit', 'Noto Sans SC', sans-serif;
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }
        
        .glass-panel {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        
        header {
            text-align: center;
            margin-bottom: 40px;
            position: relative;
        }
        
        h1 {
            font-size: 2.5rem;
            font-weight: 800;
            margin: 0;
            background: var(--primary-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.05em;
        }
        
        h2 {
            font-size: 1.5rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
            margin-top: 0;
            font-weight: 600;
            color: #a855f7;
        }
        
        .subtitle {
            color: var(--text-muted);
            font-size: 1.1rem;
            margin-top: 10px;
        }
        
        .meta-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
        }
        
        .meta-item {
            display: flex;
            flex-direction: column;
        }
        
        .meta-label {
            font-size: 0.85rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .meta-value {
            font-size: 1.2rem;
            font-weight: 600;
            margin-top: 4px;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .metric-card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.04);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-4px);
            border-color: var(--primary);
            box-shadow: 0 4px 20px rgba(99, 102, 241, 0.15);
        }
        
        .metric-val {
            font-size: 2.2rem;
            font-weight: 800;
            color: var(--text-main);
            margin: 10px 0;
            background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .metric-name {
            font-size: 0.9rem;
            color: var(--text-muted);
        }
        
        .flex-layout {
            display: flex;
            flex-wrap: wrap;
            gap: 24px;
        }
        
        .column-6 {
            flex: 1;
            min-width: 45%;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        
        th, td {
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }
        
        th {
            font-weight: 600;
            color: var(--text-muted);
            font-size: 0.9rem;
        }
        
        tr:hover {
            background-color: rgba(255, 255, 255, 0.02);
        }
        
        .plot-container {
            text-align: center;
            margin-top: 20px;
        }
        
        .plot-img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }
        
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        .badge-success {
            background-color: rgba(16, 185, 129, 0.15);
            color: var(--accent-green);
        }
        
        .badge-info {
            background-color: rgba(99, 102, 241, 0.15);
            color: var(--primary);
        }
        
        footer {
            text-align: center;
            margin-top: 60px;
            font-size: 0.85rem;
            color: var(--text-muted);
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="glass-panel">
            <h1>scAnnoRare 评估报告</h1>
            <div class="subtitle">单细胞细胞类型注释与稀有细胞识别多方法评估系统 V1.0</div>
        </header>
        
        <!-- Metadata -->
        <section class="glass-panel">
            <h2>实验基本信息</h2>
            <div class="meta-grid">
                <div class="meta-item">
                    <span class="meta-label">评估方法</span>
                    <span class="meta-value">{{ method_name }}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">任务类型</span>
                    <span class="meta-value">
                        {% if task_type == 'annotation_evaluation' %}
                        细胞类型注释评估
                        {% else %}
                        稀有细胞识别评估
                        {% endif %}
                    </span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">数据配对率</span>
                    <span class="meta-value">{{ match_rate * 100 }}%</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">评估时间</span>
                    <span class="meta-value">{{ report_time }}</span>
                </div>
            </div>
        </section>
        
        <!-- Overall Metrics -->
        <section class="glass-panel">
            <h2>整体评估指标</h2>
            <div class="metrics-grid">
                {% if task_type == 'annotation_evaluation' %}
                    <div class="metric-card">
                        <div class="metric-name">Accuracy (准确率)</div>
                        <div class="metric-val">{{ overall_metrics.accuracy }}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-name">Balanced Accuracy</div>
                        <div class="metric-val">{{ overall_metrics.balanced_accuracy }}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-name">Macro F1</div>
                        <div class="metric-val">{{ overall_metrics.macro_f1 }}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-name">Weighted F1</div>
                        <div class="metric-val">{{ overall_metrics.weighted_f1 }}</div>
                    </div>
                {% else %}
                    {% if overall_metrics.rare_precision is defined %}
                        <div class="metric-card">
                            <div class="metric-name">Rare Precision</div>
                            <div class="metric-val">{{ overall_metrics.rare_precision }}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-name">Rare Recall</div>
                            <div class="metric-val">{{ overall_metrics.rare_recall }}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-name">Rare F1</div>
                            <div class="metric-val">{{ overall_metrics.rare_f1 }}</div>
                        </div>
                        {% if overall_metrics.auroc is not none %}
                        <div class="metric-card">
                            <div class="metric-name">AUROC</div>
                            <div class="metric-val">{{ overall_metrics.auroc }}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-name">AUPRC</div>
                            <div class="metric-val">{{ overall_metrics.auprc }}</div>
                        </div>
                        {% endif %}
                    {% else %}
                        <div class="metric-card">
                            <div class="metric-name">Macro Rare F1</div>
                            <div class="metric-val">{{ overall_metrics.macro_rare_f1 }}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-name">Macro Rare Recall</div>
                            <div class="metric-val">{{ overall_metrics.macro_rare_recall }}</div>
                        </div>
                    {% endif %}
                {% endif %}
            </div>
        </section>
        
        <!-- Detailed Results & Plots -->
        <div class="flex-layout">
            <!-- Table Section -->
            <div class="column-6 glass-panel">
                <h2>分类详细指标</h2>
                <table>
                    <thead>
                        {% if task_type == 'annotation_evaluation' %}
                        <tr>
                            <th>细胞类型 (Class)</th>
                            <th>Precision</th>
                            <th>Recall</th>
                            <th>F1-Score</th>
                            <th>Cell Count</th>
                        </tr>
                        {% else %}
                        <tr>
                            <th>评估指标 / 类别</th>
                            <th>数值 / 分类</th>
                            <th>尝试次数</th>
                            <th>错误恢复</th>
                            <th>错误恢复率</th>
                        </tr>
                        {% endif %}
                    </thead>
                    <tbody>
                        {% if task_type == 'annotation_evaluation' %}
                            {% for cls, met in per_class_metrics.items() %}
                            <tr>
                                <td><strong>{{ cls }}</strong></td>
                                <td>{{ met.precision }}</td>
                                <td>{{ met.recall }}</td>
                                <td>{{ met.f1 }}</td>
                                <td><span class="badge badge-info">{{ met.support }}</span></td>
                            </tr>
                            {% endfor %}
                        {% else %}
                            {% if per_class_metrics is defined %}
                                {% for cls, met in per_class_metrics.items() %}
                                <tr>
                                    <td><strong>{{ cls }} (稀有类)</strong></td>
                                    <td>F1: {{ met.rare_f1 }}</td>
                                    <td>P: {{ met.rare_precision }} | R: {{ met.rare_recall }}</td>
                                    <td>FN: {{ met.false_negative_count }}</td>
                                    <td>FP: {{ met.false_positive_count }}</td>
                                </tr>
                                {% endfor %}
                            {% else %}
                                <tr>
                                    <td><strong>整体稀有细胞识别 (Rare Class)</strong></td>
                                    <td>F1: {{ overall_metrics.rare_f1 }}</td>
                                    <td>P: {{ overall_metrics.rare_precision }} | R: {{ overall_metrics.rare_recall }}</td>
                                    <td>FP count: {{ overall_metrics.false_positive_count }}</td>
                                    <td>Missed: {{ overall_metrics.missed_rare_count }}</td>
                                </tr>
                            {% endif %}
                            
                            {% if false_rescue_rate is not none %}
                                {% for cls, frr in false_rescue_rate.items() %}
                                <tr>
                                    <td><strong>{{ cls }} False Rescue Rate</strong></td>
                                    <td><span class="badge badge-success">{{ frr.false_rescue_rate }}</span></td>
                                    <td>{{ frr.rescue_attempt_count }}</td>
                                    <td>{{ frr.false_rescue_count }}</td>
                                    <td>-</td>
                                </tr>
                                {% endfor %}
                            {% endif %}
                        {% endif %}
                    </tbody>
                </table>
            </div>
            
            <!-- Figures Section -->
            <div class="column-6 glass-panel">
                <h2>可视化分析图表</h2>
                <div class="plot-container">
                    {% if task_type == 'annotation_evaluation' %}
                        <img class="plot-img" src="figures/confusion_matrix.png" alt="混淆矩阵" onerror="this.style.display='none'">
                        <p class="subtitle">图 1: 混淆矩阵 (Confusion Matrix) 分布</p>
                    {% else %}
                        {% if overall_metrics.auroc is not none %}
                            <img class="plot-img" src="figures/roc_pr_curve.png" alt="ROC & PR 曲线" onerror="this.style.display='none'">
                            <p class="subtitle">图 1: 稀有细胞分类 ROC 与 PR 曲线分析</p>
                        {% else %}
                            <img class="plot-img" src="figures/confusion_matrix.png" alt="稀有细胞混淆矩阵" onerror="this.style.display='none'">
                            <p class="subtitle">图 1: 稀有细胞检测混淆矩阵</p>
                        {% endif %}
                    {% endif %}
                </div>
            </div>
        </div>
        
        <footer>
            <p>© 2026 scAnnoRare. 基于 Web-Agent 协同架构的单细胞数据评估系统.</p>
        </footer>
    </div>
</body>
</html>
"""

def generate_report(result_json_path: str, output_dir: str):
    logger.info(f"Generating offline report from {result_json_path}")
    
    with open(result_json_path, "r", encoding="utf-8") as f:
        res = json.load(f)
        
    if not res.get("success", False):
        raise ValueError("Input result.json contains failure status.")
        
    task_type = res.get("task_type")
    method_name = res.get("method_name", "Unknown Method")
    match_rate = res.get("matching_summary", {}).get("match_rate", 1.0)
    
    # 1. Generate Figures using matplotlib (Curated dark style to match Outfit web theme)
    plt.style.use('dark_background')
    fig_dir = os.path.join(output_dir, "figures")
    os.makedirs(fig_dir, exist_ok=True)
    
    if task_type == "annotation_evaluation":
        # Draw Confusion Matrix
        cm_data = res.get("confusion_matrix", {})
        matrix = cm_data.get("matrix", [])
        classes = cm_data.get("classes", [])
        
        if len(matrix) > 0:
            plt.figure(figsize=(10, 8), dpi=150)
            sns.heatmap(
                matrix, 
                annot=True, 
                fmt="d", 
                cmap="Purples", 
                xticklabels=classes, 
                yticklabels=classes,
                cbar_kws={'label': '细胞数'}
            )
            plt.title(f"{method_name} - 细胞类型分类混淆矩阵", fontsize=14, fontweight="bold", pad=15)
            plt.xlabel("预测类别 (Predicted Labels)", fontsize=11, labelpad=10)
            plt.ylabel("真实类别 (True Labels)", fontsize=11, labelpad=10)
            plt.xticks(rotation=45, ha='right')
            plt.yticks(rotation=0)
            plt.tight_layout()
            plt.savefig(os.path.join(fig_dir, "confusion_matrix.png"))
            plt.close()
            
    elif task_type == "rare_detection_evaluation":
        # Check if ROC/PR curve points are available
        metrics = res.get("overall_metrics", {})
        roc = metrics.get("roc_curve")
        pr = metrics.get("pr_curve")
        
        if roc and pr:
            # Draw combined ROC and PR plot side by side
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.5), dpi=150)
            
            # ROC
            ax1.plot(roc["fpr"], roc["tpr"], color="#a855f7", lw=2.5, label=f"ROC (AUC = {metrics.get('auroc'):.2f})")
            ax1.plot([0, 1], [0, 1], color="#9ca3af", linestyle="--")
            ax1.set_xlim([0.0, 1.0])
            ax1.set_ylim([0.0, 1.05])
            ax1.set_xlabel("False Positive Rate", labelpad=8)
            ax1.set_ylabel("True Positive Rate", labelpad=8)
            ax1.set_title("Receiver Operating Characteristic (ROC)", fontsize=11, fontweight="bold")
            ax1.legend(loc="lower right")
            ax1.grid(alpha=0.15)
            
            # PR
            ax2.plot(pr["recall"], pr["precision"], color="#6366f1", lw=2.5, label=f"PR (AUPRC = {metrics.get('auprc'):.2f})")
            ax2.set_xlim([0.0, 1.0])
            ax2.set_ylim([0.0, 1.05])
            ax2.set_xlabel("Recall (召回率)", labelpad=8)
            ax2.set_ylabel("Precision (精确率)", labelpad=8)
            ax2.set_title("Precision-Recall Curve (PR)", fontsize=11, fontweight="bold")
            ax2.legend(loc="lower left")
            ax2.grid(alpha=0.15)
            
            plt.suptitle(f"{method_name} - 稀有细胞检测性能曲线", fontsize=14, fontweight="bold", y=0.98)
            plt.tight_layout()
            plt.savefig(os.path.join(fig_dir, "roc_pr_curve.png"))
            plt.close()
        else:
            # Fallback to binary confusion matrix
            cm = metrics.get("confusion_matrix", {})
            if cm:
                cm_matrix = [[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]]
                plt.figure(figsize=(6, 5), dpi=150)
                sns.heatmap(
                    cm_matrix,
                    annot=True,
                    fmt="d",
                    cmap="Blues",
                    xticklabels=["预测非稀有", "预测稀有"],
                    yticklabels=["真实非稀有", "真实稀有"]
                )
                plt.title(f"{method_name} - 稀有细胞检测混淆矩阵", fontsize=12, fontweight="bold", pad=15)
                plt.tight_layout()
                plt.savefig(os.path.join(fig_dir, "confusion_matrix.png"))
                plt.close()

    # 2. Render Template
    t = Template(HTML_TEMPLATE)
    html_content = t.render(
        method_name=method_name,
        task_type=task_type,
        match_rate=match_rate,
        report_time=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        overall_metrics=res.get("overall_metrics", {}),
        per_class_metrics=res.get("per_class_metrics", {}),
        false_rescue_rate=res.get("false_rescue_rate"),
    )
    
    report_path = os.path.join(output_dir, "report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    logger.info(f"Successfully generated HTML offline report at {report_path}")
    return report_path

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_report.py <result_json> <output_dir>")
        sys.exit(1)
        
    res_path = sys.argv[1]
    out_dir = sys.argv[2]
    
    try:
        generate_report(res_path, out_dir)
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        sys.exit(1)
