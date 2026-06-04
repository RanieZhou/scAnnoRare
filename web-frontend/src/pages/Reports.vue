<template>
  <div class="reports-page">
    <!-- Filter bar -->
    <div class="filter-bar glass-card">
      <span class="filter-label">🗂 筛选实验：</span>
      <el-select
        v-model="filterExpId"
        placeholder="全部实验"
        clearable
        style="width: 300px;"
        class="neon-select"
        @change="fetchReports"
      >
        <el-option v-for="e in experiments" :key="e.id" :label="e.experiment_name" :value="e.id" />
      </el-select>
      <el-button type="primary" plain size="small" :loading="loading" @click="fetchReports">
        刷新
      </el-button>
    </div>

    <!-- Empty -->
    <div v-if="!loading && reports.length === 0" class="glass-card empty-state">
      <el-empty description="暂无报告。完成评估任务后，报告将自动出现在此处。" />
    </div>

    <!-- Report cards -->
    <div v-else class="report-grid">
      <div
        v-for="r in reports"
        :key="r.id"
        class="report-card glass-card"
      >
        <div class="report-header">
          <div class="report-icon">📄</div>
          <div class="report-meta">
            <div class="report-method">{{ getMethodName(r.method_run_id) }}</div>
            <div class="report-exp">{{ getExpName(r.experiment_id) }}</div>
          </div>
          <el-tag type="success" size="small" effect="dark">HTML</el-tag>
        </div>

        <!-- Key metrics preview -->
        <div class="metrics-row" v-if="r.metrics && hasMetrics(r.metrics)">
          <div class="metric-chip" v-if="r.metrics.accuracy != null">
            <span class="chip-lbl">Accuracy</span>
            <span class="chip-val">{{ r.metrics.accuracy }}</span>
          </div>
          <div class="metric-chip" v-if="r.metrics.macro_f1 != null">
            <span class="chip-lbl">Macro-F1</span>
            <span class="chip-val">{{ r.metrics.macro_f1 }}</span>
          </div>
          <div class="metric-chip" v-if="r.metrics.rare_f1 != null">
            <span class="chip-lbl">Rare-F1</span>
            <span class="chip-val">{{ r.metrics.rare_f1 }}</span>
          </div>
          <div class="metric-chip" v-if="r.metrics.auroc != null">
            <span class="chip-lbl">AUROC</span>
            <span class="chip-val">{{ r.metrics.auroc }}</span>
          </div>
        </div>

        <div class="report-footer">
          <span class="report-time">{{ formatTime(r.created_at) }}</span>
          <div class="report-actions">
            <el-button size="small" type="primary" plain @click="openReport(r)">
              在线查看报告
            </el-button>
            <el-button size="small" type="info" plain @click="downloadReport(r)">
              下载 HTML
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { useAgentStore } from '../stores/agent'

const WEB        = 'http://127.0.0.1:8000'
const agentStore = useAgentStore()

const loading     = ref(false)
const reports     = ref<any[]>([])
const experiments = ref<any[]>([])
const methodRuns  = ref<any[]>([])
const filterExpId = ref('')

onMounted(async () => {
  await Promise.all([fetchExperiments(), fetchReports()])
})

async function fetchExperiments() {
  try {
    const res = await axios.get(`${WEB}/api/v1/experiments`)
    experiments.value = res.data
    // also pre-load method runs for name lookups
    for (const e of res.data) {
      try {
        const r = await axios.get(`${WEB}/api/v1/experiments/${e.id}/method-runs`)
        methodRuns.value.push(...r.data)
      } catch (_) {}
    }
  } catch (_) {}
}

async function fetchReports() {
  loading.value = true
  try {
    const params: any = {}
    if (filterExpId.value) params.experiment_id = filterExpId.value
    const res = await axios.get(`${WEB}/api/v1/reports`, { params })
    reports.value = res.data
  } catch (_) {
    ElMessage.error('无法加载报告列表')
  } finally {
    loading.value = false
  }
}

function getExpName(expId: string) {
  return experiments.value.find(e => e.id === expId)?.experiment_name ?? expId
}

function getMethodName(runId: string) {
  return methodRuns.value.find(r => r.id === runId)?.method_name ?? runId
}

function hasMetrics(m: any) {
  return m && Object.keys(m).length > 0
}

function formatTime(ts: number) {
  if (!ts) return ''
  return new Date(ts * 1000).toLocaleString('zh-CN')
}

async function openReport(r: any) {
  if (!r.report_path?.startsWith('local_agent::')) {
    ElMessage.warning('报告文件不在本地 Agent 上')
    return
  }
  if (!agentStore.paired || !agentStore.isOnline) {
    ElMessage.warning('请先配对本地 Agent 才能查看在线报告')
    return
  }
  // Proxy through web backend to carry Authorization header
  const proxyUrl = `${WEB}/api/v1/reports/${r.id}/download`
    + `?session_token=${encodeURIComponent(agentStore.sessionToken)}`
    + `&agent_url=${encodeURIComponent(agentStore.agentUrl)}`
  window.open(proxyUrl, '_blank')
}

async function downloadReport(r: any) {
  if (!r.report_path?.startsWith('local_agent::')) {
    ElMessage.warning('无可下载的本地报告')
    return
  }
  const localJobId = r.report_path.split('::')[1]
  if (!agentStore.paired || !agentStore.isOnline) {
    ElMessage.warning('请先配对本地 Agent 才能下载报告')
    return
  }
  try {
    const resp = await axios.get(
      `${agentStore.agentUrl}/api/v1/local/tasks/${localJobId}/report`,
      {
        responseType: 'blob',
        headers: { Authorization: `Bearer ${agentStore.sessionToken}` },
      },
    )
    const url  = URL.createObjectURL(new Blob([resp.data], { type: 'text/html' }))
    const link = document.createElement('a')
    link.href     = url
    link.download = `scannorare_report_${localJobId}.html`
    link.click()
    URL.revokeObjectURL(url)
  } catch (_) {
    ElMessage.error('下载失败，请检查 Agent 连接')
  }
}
</script>

<style scoped>
.reports-page { display: flex; flex-direction: column; gap: 24px; }

.glass-card {
  background: rgba(22, 28, 36, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.2);
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  padding: 16px 24px;
}
.filter-label { font-weight: 600; color: #cbd5e1; white-space: nowrap; }

.empty-state { display: flex; align-items: center; justify-content: center; min-height: 300px; }

.report-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 20px;
}

.report-card { display: flex; flex-direction: column; gap: 16px; transition: transform 0.2s; }
.report-card:hover { transform: translateY(-3px); }

.report-header {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}
.report-icon   { font-size: 2rem; }
.report-meta   { flex-grow: 1; }
.report-method { font-size: 1.05rem; font-weight: 700; color: #f1f5f9; margin-bottom: 4px; }
.report-exp    { font-size: 0.82rem; color: #64748b; }

.metrics-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.metric-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: rgba(99,102,241,0.08);
  border: 1px solid rgba(99,102,241,0.18);
  border-radius: 10px;
  padding: 6px 14px;
  min-width: 70px;
}
.chip-lbl { font-size: 0.72rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.04em; }
.chip-val { font-size: 1.05rem; font-weight: 700; color: #a5b4fc; margin-top: 2px; }

.report-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 4px;
  padding-top: 12px;
  border-top: 1px solid rgba(255,255,255,0.05);
}
.report-time    { font-size: 0.82rem; color: #475569; }
.report-actions { display: flex; gap: 8px; }
</style>
