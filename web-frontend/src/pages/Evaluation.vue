<template>
  <div class="evaluation-page">
    <!-- Top Selector Bar -->
    <div class="top-selector-bar glass-card">
      <div class="selector-content">
        <span class="selector-label">🧬 选择实验主题：</span>
        <el-select
          v-model="activeExpId"
          placeholder="请选择基准实验进行对比分析"
          class="neon-select"
          style="width: 350px;"
          @change="handleExperimentChange"
        >
          <el-option v-for="e in experiments" :key="e.id" :label="e.experiment_name" :value="e.id" />
        </el-select>
      </div>
      <div v-if="activeExp" class="active-exp-specs">
        <el-tag :type="activeExp.task_type === 'annotation_evaluation' ? 'success' : 'warning'" effect="dark">
          {{ activeExp.task_type === 'annotation_evaluation' ? '类型注释任务' : '稀有识别任务' }}
        </el-tag>
        <span class="spec-label">数据集：</span><strong class="text-glow">{{ activeExp.dataset_name }}</strong>
        <span class="spec-label">关联标签：</span><strong>{{ activeExp.label_col }}</strong>
      </div>
    </div>

    <div v-if="!activeExpId" class="glass-card empty-state">
      <el-empty description="请在上方选择一个活跃的基准评估实验，以开启多方法管理、实时评估与指标排序对比面板" />
    </div>

    <div v-else class="evaluation-grid">
      <!-- Left panel: submit new run -->
      <div class="left-panel">
        <div class="glass-card method-adder">
          <h3 class="panel-title">➕ 导入/添加方法预测结果</h3>
          <el-form :model="methodForm" label-position="top">
            <el-form-item label="评估方法名称 (Method Name)" required>
              <el-input v-model="methodForm.methodName" placeholder="例如: CellTypist" class="neon-input" />
            </el-form-item>
            <el-form-item label="方法预测 CSV 文件绝对路径" required>
              <el-input v-model="methodForm.predictionCsv" placeholder="/data/predictions.csv" class="neon-input" />
            </el-form-item>
            <el-form-item v-if="activeExp?.task_type === 'rare_detection_evaluation'" label="修正前基线 CSV 路径（可选，用于 FRR 指标）">
              <el-input v-model="methodForm.baselineCsv" placeholder="baseline_unrescued.csv" class="neon-input" />
            </el-form-item>
            <el-button
              type="primary"
              class="gradient-btn w-100"
              :loading="addRunLoading"
              @click="handleTriggerEvaluation"
            >
              提交并在本地节点运行评估
            </el-button>
          </el-form>

          <div class="dev-quick-prediction">
            <el-divider>快速测试 CSV 路径</el-divider>
            <p class="helper-text">
              点击填入测试 CSV：
              <code class="clickable-code" @click="methodForm.predictionCsv = mockCsv">{{ mockCsv }}</code>
            </p>
          </div>
        </div>

        <!-- Running jobs list -->
        <div class="glass-card task-monitor" v-if="activeJobs.length > 0">
          <h3 class="panel-title">⏳ 任务队列与同步</h3>
          <div class="job-list">
            <div v-for="job in activeJobs" :key="job.jobId" class="job-item">
              <div class="job-header">
                <span>⚡ {{ job.methodName }}</span>
                <el-tag :type="getJobTagType(job.status)" size="small">{{ job.status }}</el-tag>
              </div>
              <el-progress :percentage="job.progress" :stroke-width="8" class="mt-2" />
              <div class="job-actions mt-2">
                <el-button size="small" type="primary" plain @click="syncJob(job.jobId)">同步进度</el-button>
                <el-button size="small" type="info" plain @click="viewJobLogs(job.jobId)">查看运行日志</el-button>
                <el-button
                  v-if="job.status === 'success'"
                  size="small"
                  type="success"
                  plain
                  @click="openLocalReport(job.jobId)"
                >查看报告</el-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right panel: results -->
      <div class="right-panel">
        <div class="glass-card comparison-section">
          <h3 class="panel-title">🏆 多方法指标横向对比与排序</h3>
          <div class="table-toolbar">
            <span>排序依据：</span>
            <el-select v-model="sortBy" size="small" style="width: 180px;" @change="sortComparisonTable">
              <el-option value="accuracy" label="Accuracy" />
              <el-option value="macro_f1" label="Macro-F1" />
              <el-option value="rare_f1" label="Rare-F1" />
              <el-option value="auprc" label="AUPRC" />
              <el-option value="auroc" label="AUROC" />
            </el-select>
          </div>

          <el-table :data="comparisonTable" style="width: 100%" size="small" class="dark-table mt-3">
            <el-table-column type="index" label="排名" width="55">
              <template #default="scope">
                <span class="rank-num" :class="'rank-' + (scope.$index + 1)">{{ scope.$index + 1 }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="method_name" label="评估方法" min-width="120">
              <template #default="scope"><strong>{{ scope.row.method_name }}</strong></template>
            </el-table-column>
            <el-table-column prop="accuracy"  label="Accuracy" />
            <el-table-column prop="macro_f1"  label="Macro-F1" />
            <el-table-column prop="rare_f1"   label="Rare-F1" />
            <el-table-column prop="auprc"     label="AUPRC" />
            <el-table-column prop="auroc"     label="AUROC" />
            <el-table-column label="操作" width="160">
              <template #default="scope">
                <el-button size="small" type="primary" plain @click="selectMethodRun(scope.row)">图表</el-button>
                <el-button size="small" type="success" plain @click="openReportByRunId(scope.row.method_run_id)">报告</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- Interactive ECharts -->
        <div class="glass-card chart-visualization" v-if="selectedRunId">
          <h3 class="panel-title">📊 评估图表交互式重绘: {{ selectedMethodName }}</h3>
          <div class="visual-layout">
            <div class="chart-box">
              <div id="interactive-echart" class="interactive-echart-div"></div>
            </div>
            <div class="metrics-details-card" v-if="selectedResult">
              <h4>🎯 {{ selectedMethodName }}</h4>
              <div class="metrics-bullets">
                <div class="bullet-item">
                  <span class="b-lbl">Accuracy</span>
                  <span class="b-val">{{ selectedResult.metrics?.accuracy ?? 'N/A' }}</span>
                </div>
                <div class="bullet-item">
                  <span class="b-lbl">Macro-F1</span>
                  <span class="b-val">{{ selectedResult.metrics?.macro_f1 ?? 'N/A' }}</span>
                </div>
                <div v-if="activeExp?.task_type === 'rare_detection_evaluation'" class="bullet-item">
                  <span class="b-lbl">Rare F1</span>
                  <span class="b-val">{{ selectedResult.metrics?.rare_f1 ?? 'N/A' }}</span>
                </div>
                <div v-if="activeExp?.task_type === 'rare_detection_evaluation'" class="bullet-item">
                  <span class="b-lbl">AUPRC</span>
                  <span class="b-val">{{ selectedResult.metrics?.auprc ?? 'N/A' }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Logs dialog -->
    <el-dialog v-model="logsVisible" title="Local Agent 运行日志" width="70%" class="dark-dialog">
      <div class="logs-container">
        <h4>stdout：</h4>
        <pre class="log-block">{{ jobLogs.stdout || '暂无日志...' }}</pre>
        <h4 class="mt-3">stderr：</h4>
        <pre class="log-block err">{{ jobLogs.stderr || '无异常' }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { useAgentStore } from '../stores/agent'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import * as echarts from 'echarts'

const WEB = 'http://127.0.0.1:8000'
const agentStore = useAgentStore()

// ── state ─────────────────────────────────────────────────────────────────────
const activeExpId   = ref('')
const activeExp     = ref<any>(null)
const experiments   = ref<any[]>([])
const addRunLoading = ref(false)
const sortBy        = ref('macro_f1')
const comparisonTable = ref<any[]>([])
const mockCsv = ref('')

const methodForm = reactive({ methodName: 'CellTypist', predictionCsv: '', baselineCsv: '' })

interface JobEntry {
  jobId: string        // web-backend job id
  localJobId: string   // agent-side job id
  methodName: string
  status: string
  progress: number
}
const activeJobs = ref<JobEntry[]>([])

const selectedRunId     = ref('')
const selectedMethodName = ref('')
const selectedResult    = ref<any>(null)

const logsVisible = ref(false)
const jobLogs     = ref<any>({ stdout: '', stderr: '' })

// ── init ──────────────────────────────────────────────────────────────────────
onMounted(async () => {
  await fetchExperiments()
  const isWindows = navigator.platform.toLowerCase().includes('win')
  mockCsv.value = isWindows
    ? 'C:\\Users\\username\\Desktop\\scAnnoRare\\local-agent\\workspace\\predictions\\imported_predictions\\tiny_predictions.csv'
    : '/Users/wangxiansheng/Desktop/scAnnoRare/local-agent/workspace/predictions/imported_predictions/tiny_predictions.csv'
})

// ── experiments ───────────────────────────────────────────────────────────────
async function fetchExperiments() {
  try {
    const res = await axios.get(`${WEB}/api/v1/experiments`)
    experiments.value = res.data
  } catch (_) {}
}

async function handleExperimentChange(val: string) {
  activeExp.value = experiments.value.find(e => e.id === val) ?? null
  if (activeExp.value) {
    try {
      const r = await axios.get(`${WEB}/api/v1/datasets/${activeExp.value.dataset_id}`)
      activeExp.value.dataset_name = r.data.dataset_name
    } catch (_) {}
    selectedRunId.value = ''
    await fetchComparisonData()
  }
}

// ── comparison ────────────────────────────────────────────────────────────────
async function fetchComparisonData() {
  if (!activeExpId.value) return
  try {
    const res = await axios.get(`${WEB}/api/v1/experiments/${activeExpId.value}/comparison`)
    comparisonTable.value = res.data.comparison_table
    sortComparisonTable()
  } catch (_) {}
}

function sortComparisonTable() {
  const m = sortBy.value
  comparisonTable.value.sort((a, b) => {
    const va = a[m] === 'N/A' || a[m] == null ? -1 : Number(a[m])
    const vb = b[m] === 'N/A' || b[m] == null ? -1 : Number(b[m])
    return vb - va
  })
}

// ── trigger evaluation ────────────────────────────────────────────────────────
async function handleTriggerEvaluation() {
  if (!methodForm.predictionCsv.trim()) {
    ElMessage.warning('请输入预测结果 CSV 绝对路径')
    return
  }
  if (!agentStore.paired) {
    ElMessage.warning('请先在「Local Agent」页面完成配对')
    return
  }
  addRunLoading.value = true
  try {
    // 1. Create method run in web backend
    const runRes = await axios.post(
      `${WEB}/api/v1/experiments/${activeExpId.value}/method-runs`,
      {
        experiment_id: activeExpId.value,
        method_name: methodForm.methodName,
        method_type: 'custom_prediction',
        input_type: 'prediction_csv',
        prediction_file_alias: methodForm.predictionCsv,
        baseline_file_alias: methodForm.baselineCsv || null,
      },
    )
    const methodRun = runRes.data.method_run

    // 2. Dispatch job via web backend (session_token passed in body, not URL)
    const jobRes = await axios.post(`${WEB}/api/v1/jobs`, {
      method_run_id: methodRun.id,
      agent_url: agentStore.agentUrl,
      session_token: agentStore.sessionToken,
    })

    if (jobRes.data.success) {
      ElMessage.success('评估任务已成功下发至 Local Agent！')
      activeJobs.value.push({
        jobId: jobRes.data.job_id,
        localJobId: jobRes.data.local_job_id,
        methodName: methodForm.methodName,
        status: 'running',
        progress: 10,
      })
      startPolling(jobRes.data.job_id)
    }
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail ?? '评估下发失败，请检查 CSV 路径及 Local Agent 连接')
  } finally {
    addRunLoading.value = false
  }
}

// ── polling ───────────────────────────────────────────────────────────────────
function startPolling(jobId: string) {
  const t = setInterval(async () => {
    try {
      const res = await axios.post(
        `${WEB}/api/v1/jobs/${jobId}/sync`,
        null,
        { params: { session_token: agentStore.sessionToken, agent_url: agentStore.agentUrl } },
      )
      const entry = activeJobs.value.find(j => j.jobId === jobId)
      if (!entry) { clearInterval(t); return }
      entry.status   = res.data.status
      entry.progress = res.data.progress
      if (res.data.status === 'success') {
        clearInterval(t)
        ElMessage.success(`方法 ${entry.methodName} 评估完成！`)
        await fetchComparisonData()
        const row = comparisonTable.value.find(c => c.method_name === entry.methodName)
        if (row) selectMethodRun(row)
      } else if (['failed', 'cancelled'].includes(res.data.status)) {
        clearInterval(t)
        ElMessage.error(`方法 ${entry.methodName} 评估失败，请查看日志`)
      }
    } catch (_) { clearInterval(t) }
  }, 2500)
}

// ── manual sync ───────────────────────────────────────────────────────────────
async function syncJob(jobId: string) {
  try {
    const res = await axios.post(
      `${WEB}/api/v1/jobs/${jobId}/sync`,
      null,
      { params: { session_token: agentStore.sessionToken, agent_url: agentStore.agentUrl } },
    )
    const entry = activeJobs.value.find(j => j.jobId === jobId)
    if (entry) { entry.status = res.data.status; entry.progress = res.data.progress }
    if (res.data.status === 'success') await fetchComparisonData()
  } catch (_) { ElMessage.error('同步失败') }
}

// ── logs ──────────────────────────────────────────────────────────────────────
async function viewJobLogs(jobId: string) {
  try {
    const res = await axios.get(`${WEB}/api/v1/jobs/${jobId}/logs`, {
      params: { session_token: agentStore.sessionToken, agent_url: agentStore.agentUrl },
    })
    jobLogs.value = res.data
  } catch (_) {
    jobLogs.value = { stdout: '无法获取日志，请确认 Agent 在线', stderr: '' }
  }
  logsVisible.value = true
}

// ── report ────────────────────────────────────────────────────────────────────
function _proxyReportUrl(reportId: string) {
  return `${WEB}/api/v1/reports/${reportId}/download`
    + `?session_token=${encodeURIComponent(agentStore.sessionToken)}`
    + `&agent_url=${encodeURIComponent(agentStore.agentUrl)}`
}

async function openLocalReport(jobId: string) {
  try {
    const jobRes = await axios.get(`${WEB}/api/v1/jobs/${jobId}`)
    const localJobId = jobRes.data.local_job_id
    if (!localJobId) { ElMessage.warning('该任务暂无报告'); return }

    // Look up the corresponding Report record by job_id
    const repsRes = await axios.get(`${WEB}/api/v1/reports`,
      { params: { experiment_id: activeExpId.value } })
    const report = (repsRes.data as any[]).find((r: any) => r.job_id === jobId)
    if (report) {
      window.open(_proxyReportUrl(report.id), '_blank')
    } else {
      ElMessage.warning('报告记录尚未生成，请稍后再试')
    }
  } catch (_) {
    ElMessage.error('无法获取报告')
  }
}

async function openReportByRunId(methodRunId: string) {
  try {
    const res = await axios.get(`${WEB}/api/v1/reports`,
      { params: { experiment_id: activeExpId.value } })
    const report = (res.data as any[]).find((r: any) => r.method_run_id === methodRunId)
    if (report) {
      window.open(_proxyReportUrl(report.id), '_blank')
    } else {
      ElMessage.warning('暂无可用报告')
    }
  } catch (_) { ElMessage.error('无法获取报告') }
}

// ── interactive charts ────────────────────────────────────────────────────────
async function selectMethodRun(row: any) {
  selectedRunId.value      = row.method_run_id
  selectedMethodName.value = row.method_name
  try {
    const res = await axios.get(`${WEB}/api/v1/method-runs/${row.method_run_id}/result`)
    selectedResult.value = res.data
    nextTick(renderCharts)
  } catch (_) { ElMessage.error('无法拉取图表数据') }
}

function renderCharts() {
  if (!selectedResult.value) return
  const dom = document.getElementById('interactive-echart')
  if (!dom) return
  const chart = echarts.init(dom, 'dark')
  chart.clear()

  if (activeExp.value?.task_type === 'annotation_evaluation') {
    const cm = selectedResult.value.confusion_matrix
    if (!cm?.matrix?.length) return
    const data: [number, number, number][] = []
    cm.matrix.forEach((row: number[], i: number) =>
      row.forEach((v: number, j: number) => data.push([j, i, v]))
    )
    chart.setOption({
      backgroundColor: 'transparent',
      tooltip: { position: 'top' },
      grid: { height: '70%', top: '10%' },
      xAxis: { type: 'category', data: cm.classes, splitArea: { show: true }, axisLabel: { rotate: 45 } },
      yAxis: { type: 'category', data: cm.classes, splitArea: { show: true } },
      visualMap: {
        min: 0,
        max: Math.max(...data.map(d => d[2])),
        calculable: true, orient: 'horizontal', left: 'center', bottom: '0%',
        inRange: { color: ['rgba(99,102,241,0.05)', '#6366f1', '#a855f7'] },
      },
      series: [{ name: '细胞数', type: 'heatmap', data, label: { show: true } }],
    })
  } else {
    const curve = selectedResult.value.curve_data
    if (curve?.roc_curve) {
      const pts = curve.roc_curve.fpr.map((f: number, i: number) => [f, curve.roc_curve.tpr[i]])
      chart.setOption({
        backgroundColor: 'transparent',
        title: { text: 'ROC 曲线', left: 'center', textStyle: { fontSize: 13 } },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'value', name: 'FPR' },
        yAxis: { type: 'value', name: 'TPR' },
        series: [{ data: pts, type: 'line', smooth: true, color: '#a855f7', lineStyle: { width: 3 }, areaStyle: { color: 'rgba(168,85,247,0.1)' } }],
      })
    }
  }
}

function getJobTagType(status: string) {
  const m: Record<string, string> = { success: 'success', failed: 'danger', running: 'warning', cancelled: 'info' }
  return m[status] ?? 'info'
}
</script>

<style scoped>
.evaluation-page { display: flex; flex-direction: column; gap: 24px; }

.glass-card {
  background: rgba(22, 28, 36, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.2);
}

.top-selector-bar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px; }
.selector-content { display: flex; align-items: center; }
.selector-label   { font-weight: 600; color: #cbd5e1; }
.active-exp-specs { display: flex; align-items: center; gap: 12px; font-size: 0.9rem; }
.spec-label       { color: #64748b; margin-left: 8px; }
.text-glow        { color: #a855f7; text-shadow: 0 0 8px rgba(168,85,247,0.3); }

.evaluation-grid  { display: flex; gap: 24px; align-items: flex-start; }
.left-panel       { width: 380px; flex-shrink: 0; display: flex; flex-direction: column; gap: 24px; }
.right-panel      { flex-grow: 1; display: flex; flex-direction: column; gap: 24px; }
.panel-title      { margin: 0 0 20px; font-size: 1.1rem; font-weight: 700; color: #cbd5e1; }
.w-100            { width: 100%; }

.gradient-btn {
  background: var(--primary-gradient, linear-gradient(135deg,#6366f1,#a855f7)) !important;
  border: none !important; color: white !important; font-weight: 600;
}

.dev-quick-prediction { margin-top: 24px; font-size: 0.8rem; color: #64748b; }
.clickable-code {
  display: block; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
  border-radius: 6px; padding: 8px; margin-top: 6px; font-family: monospace; color: #6366f1;
  cursor: pointer; word-break: break-all; transition: all .3s;
}
.clickable-code:hover { background: rgba(99,102,241,0.08); border-color: rgba(99,102,241,0.3); }

.job-item { background: rgba(255,255,255,0.01); border: 1px solid rgba(255,255,255,0.04); padding: 16px; border-radius: 12px; margin-bottom: 12px; }
.job-header { display: flex; justify-content: space-between; font-weight: 600; }
.job-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.mt-2 { margin-top: 8px; }
.mt-3 { margin-top: 12px; }

.table-toolbar { display: flex; align-items: center; gap: 8px; font-size: 0.9rem; }
.rank-num { display: inline-block; width: 22px; height: 22px; border-radius: 50%; text-align: center; line-height: 22px; font-weight: 700; font-size: 0.85rem; background: rgba(255,255,255,0.06); }
.rank-1 { background: #eab308; color: #000; }
.rank-2 { background: #cbd5e1; color: #000; }
.rank-3 { background: #b45309; color: #fff; }

.visual-layout        { display: flex; gap: 20px; }
.chart-box            { flex-grow: 1; }
.interactive-echart-div { width: 100%; height: 380px; }
.metrics-details-card {
  width: 250px; flex-shrink: 0;
  background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
  border-radius: 12px; padding: 16px;
}
.metrics-details-card h4 { margin: 0 0 16px; }
.metrics-bullets { display: flex; flex-direction: column; gap: 12px; }
.bullet-item { display: flex; justify-content: space-between; font-size: 0.9rem; border-bottom: 1px dashed rgba(255,255,255,0.06); padding-bottom: 8px; }
.b-lbl { color: #64748b; }
.b-val { font-weight: 700; }

.log-block { background: #000; color: #10b981; padding: 16px; border-radius: 8px; font-family: monospace; max-height: 200px; overflow-y: auto; margin: 8px 0 0; }
.log-block.err { color: #ef4444; }
.empty-state { display: flex; align-items: center; justify-content: center; min-height: 400px; }
</style>
