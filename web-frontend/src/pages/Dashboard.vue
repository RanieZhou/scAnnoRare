<template>
  <div class="dashboard-page">
    <div class="welcome-banner glass-card">
      <div class="banner-content">
        <h2>欢迎使用 scAnnoRare 评估系统</h2>
        <p>基于 Web-Agent 协同架构的单细胞细胞类型注释与稀有细胞识别多方法基准评估平台。计算任务在本地安全运行，元数据与可视化结果由云端统一聚合管理。</p>
      </div>
      <div class="banner-action">
        <el-button type="primary" size="large" @click="$router.push('/agent')" class="gradient-btn">
          配对本地计算节点
        </el-button>
      </div>
    </div>

    <!-- Statistics Cards -->
    <div class="stats-grid">
      <div class="stat-card glass-card">
        <div class="stat-icon icon-blue"><el-icon><Folder /></el-icon></div>
        <div class="stat-info">
          <span class="stat-label">注册数据集</span>
          <span class="stat-value">2 个</span>
        </div>
      </div>
      <div class="stat-card glass-card">
        <div class="stat-icon icon-purple"><el-icon><Compass /></el-icon></div>
        <div class="stat-info">
          <span class="stat-label">配置实验主题</span>
          <span class="stat-value">3 个</span>
        </div>
      </div>
      <div class="stat-card glass-card">
        <div class="stat-icon icon-green"><el-icon><VideoPlay /></el-icon></div>
        <div class="stat-info">
          <span class="stat-label">已评估方法结果</span>
          <span class="stat-value">5 次</span>
        </div>
      </div>
    </div>

    <!-- Workflow and Activity Grid -->
    <div class="layout-grid">
      <!-- Workflow Card -->
      <div class="workflow-card glass-card">
        <h3>🔮 scAnnoRare 评估流程说明</h3>
        <div class="steps-flow">
          <div class="step-node">
            <div class="step-num">1</div>
            <h4>启动 Local Agent</h4>
            <p>在本地终端或桌面端启动 Agent，监听 17890 端口并生成配对码</p>
          </div>
          <div class="step-line">➔</div>
          <div class="step-node">
            <div class="step-num">2</div>
            <h4>注册 H5AD 数据</h4>
            <p>选择本地 .h5ad 路径，轻量级提取观测列、真实标签分布与稀有细胞候选</p>
          </div>
          <div class="step-line">➔</div>
          <div class="step-node">
            <div class="step-num">3</div>
            <h4>配置评估实验</h4>
            <p>选定标签、设置稀有阈值 (1%, 3%, 5%)，选定目标稀有细胞类型</p>
          </div>
          <div class="step-line">➔</div>
          <div class="step-node">
            <div class="step-num">4</div>
            <h4>导入并运行计算</h4>
            <p>上传算法预测所得 CSV 结果，本地 Agent 运行精准对齐并计算高维指标</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// Basic dashboard landing page setup
</script>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.glass-card {
  background: rgba(22, 28, 36, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
}

/* Banner */
.welcome-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(168, 85, 247, 0.05) 100%);
  border-left: 4px solid var(--primary-color);
}

.welcome-banner h2 {
  font-size: 1.6rem;
  font-weight: 700;
  margin: 0 0 10px 0;
  letter-spacing: -0.02em;
}

.welcome-banner p {
  color: #94a3b8;
  margin: 0;
  max-width: 800px;
}

.gradient-btn {
  background: var(--primary-gradient) !important;
  border: none !important;
  color: white !important;
  font-weight: 600;
  box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
  transition: all 0.3s ease;
}

.gradient-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
}

/* Stats */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 20px;
  transition: transform 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-4px);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.6rem;
}

.icon-blue {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.icon-purple {
  background: rgba(168, 85, 247, 0.15);
  color: #a855f7;
  border: 1px solid rgba(168, 85, 247, 0.2);
}

.icon-green {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-label {
  color: #64748b;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: 1.8rem;
  font-weight: 800;
  margin-top: 4px;
  color: #f8fafc;
}

/* Workflow */
.layout-grid {
  display: flex;
  flex-direction: column;
}

.workflow-card h3 {
  margin-top: 0;
  margin-bottom: 24px;
  font-size: 1.2rem;
  font-weight: 700;
}

.steps-flow {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.step-node {
  flex: 1;
  min-width: 200px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.step-num {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--primary-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.1rem;
  box-shadow: 0 4px 10px rgba(99, 102, 241, 0.3);
}

.step-node h4 {
  font-size: 1rem;
  margin: 16px 0 8px 0;
  color: #f1f5f9;
}

.step-node p {
  font-size: 0.85rem;
  color: #64748b;
  margin: 0;
  line-height: 1.4;
}

.step-line {
  font-size: 1.5rem;
  color: rgba(255, 255, 255, 0.1);
  padding-top: 6px;
  user-select: none;
}

@media (max-width: 768px) {
  .step-line {
    display: none;
  }
}
</style>
