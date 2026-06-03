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

    <!-- Empty state when no experiment is selected -->
    <div v-if="!activeExpId" class="glass-card empty-state">
      <el-empty description="请在上方选择一个活跃的基准评估实验，以开启多方法管理、实时评估与指标排序对比面板" />
    </div>

    <div v-else class="evaluation-grid">
      <!-- Left side: Run new Method -->
      <div class="left-panel">
        <div class="glass-card method-adder">
          <h3 class="panel-title">➕ 导入/添加方法预测结果</h3>
          <el-form :model="methodForm" label-position="top">
            <el-form-item label="评估方法名称 (Method Name)" required>
              <el-input v-model="methodForm.methodName" placeholder="例如: CellTypist" class="neon-input" />
            </el-form-item>
            
            <el-form-item label="方法预测 CSV 文件绝对路径" required>
              <el-input v-model="methodForm.predictionCsv" placeholder="C:\data\predictions.csv" class="neon-input" />
            </el-form-item>

            <el-form-item v-if="activeExp.task_type === 'rare_detection_evaluation'" label="修正前基线 CSV 路径 (可选，用于FRR指标)">
              <el-input v-model="methodForm.baselineCsv" placeholder="例如: baseline_unrescued.csv" class="neon-input" />
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
              您可使用此预置的测试 CSV 进行一键跑通：
              <code class="clickable-code" @click="methodForm.predictionCsv = mockCsv">{{ mockCsv }}</code>
            </p>
          </div>
        </div>

        <!-- Task progress list -->
        <div class="glass-card task-monitor" v-if="activeJobs.length > 0">
          <h3 class="panel-title">⏳ 任务队列与同步</h3>
          <div class="job-list">
            <div v-for="job in activeJobs" :key="job.id" class="job-item">
              <div class="job-header">
                <span>⚡ {{ job.method_name }}</span>
                <el-tag :type="getJobTagType(job.status)" size="small">{{ job.status }}</el-tag>
              </div>
              <el-progress :percentage="job.progress" :stroke-width="8" class="mt-2" />
              <div class="job-actions mt-2">
                <el-button size="small" type="primary" plain @click="syncJob(job.id)">同步进度</el-button>
                <el-button size="small" type="info" plain @click="viewJobLogs(job.id)">查看运行日志</el-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right side: Results Visualization -->
      <div class="right-panel">
        <!-- Comparative Aggregation (Section 8) -->
        <div class="glass-card comparison-section">
          <h3 class="panel-title">🏆 多方法指标横向对比与排序 (基准排行榜)</h3>
          
          <div class="table-toolbar">
            <span>排序依据：</span>
            <el-select v-model="sortBy" placeholder="选择排序指标" size="small" style="width: 180px;" @change="sortComparisonTable">
              <el-option value="accuracy" label="Accuracy" />
              <el-option value="macro_f1" label="Macro-F1" />
              <el-option value="rare_f1" label="Rare-F1" />
              <el-option value="auprc" label="AUPRC" />
              <el-option value="auroc" label="AUROC" />
            </el-select>
          </div>

          <el-table :data="comparisonTable" style="width: 100%" size="small" class="dark-table mt-3">
            <el-table-column type="index" label="排名" width="50">
              <template #default="scope">
                <span class="rank-num" :class="'rank-' + (scope.$index + 1)">{{ scope.$index + 1 }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="method_name" label="评估方法" min-width="120">
              <template #default="scope">
                <strong>{{ scope.row.method_name }}</strong>
              </template>
            </el-table-column>
            <el-table-column prop="accuracy" label="Accuracy" />
            <el-table-column prop="macro_f1" label="Macro-F1" />
            <el-table-column prop="rare_f1" label="Rare-F1" />
            <el-table-column prop="auprc" label="AUPRC" />
            <el-table-column prop="auroc" label="AUROC" />
            <el-table-column label="离线报告" width="100">
              <template #default="scope">
                <el-button size="small" type="success" plain @click="openLocalReport(scope.row.method_run_id)">打开报告</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- Interactive ECharts Plot panel -->
        <div class="glass-card chart-visualization" v-if="selectedMethodRun">
          <h3 class="panel-title">📊 评估图表交互式重绘: {{ selectedMethodName }}</h3>
          
          <div class="visual-layout">
            <!-- Heatmap / Curve container -->
            <div class="chart-box">
              <div id="interactive-echart" class="interactive-echart-div"></div>
            </div>
            
            <!-- Overall card details -->
            <div class="metrics-details-card">
              <h4>🎯 {{ selectedMethodName }} 指标汇总</h4>
              <div class="metrics-bullets" v-if="selectedResult">
                <div class="bullet-item">
                  <span class="b-lbl">Accuracy</span>
                  <span class="b-val">{{ selectedResult.metrics.accuracy || 'N/A' }}</span>
                </div>
                <div class="bullet-item">
                  <span class="b-lbl">Macro-F1</span>
                  <span class="b-val">{{ selectedResult.metrics.macro_f1 || 'N/A' }}</span>
                </div>
                <div v-if="activeExp.task_type === 'rare_detection_evaluation'" class="bullet-item">
                  <span class="b-lbl">Rare F1</span>
                  <span class="b-val">{{ selectedResult.metrics.rare_f1 || 'N/A' }}</span>
                </div>
                <div v-if="activeExp.task_type === 'rare_detection_evaluation'" class="bullet-item">
                  <span class="b-lbl">AUPRC</span>
                  <span class="b-val">{{ selectedResult.metrics.auprc || 'N/A' }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Logs Dialog -->
    <el-dialog v-model="logsVisible" title="Local Agent 运行日志流" width="70%" class="dark-dialog">
      <div class="logs-container">
        <h4>stdout 运行记录:</h4>
        <pre class="log-block">{{ jobLogs.stdout || '暂无日志输出...' }}</pre>
        <h4 class="mt-3">stderr 异常输出:</h4>
        <pre class="log-block err">{{ jobLogs.stderr || '无异常...' }}</pre>
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

const agentStore = useAgentStore()
const activeExpId = ref('')
const activeExp = ref<any>(null)
const experiments = ref<any[]>([])

const addRunLoading = ref(false)
const sortBy = ref('macro_f1')
const comparisonTable = ref<any[]>([])

// Mock csv path helper
const mockCsv = ref('')

const methodForm = reactive({
  methodName: 'CellTypist',
  predictionCsv: '',
  baselineCsv: ''
})

// Active running jobs monitor
const activeJobs = ref<any[]>([])

const fetchExperiments = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/v1/experiments')
    experiments.value = res.data
  } catch (e) {}
}

onMounted(async () => {
  await fetchExperiments()
  mockCsv.value = 'd:\\Desktop\\scAnnoRare\\local-agent\\workspace\\predictions\\imported_predictions\\tiny_predictions.csv'
})

const handleExperimentChange = async (val: string) => {
  activeExp.value = experiments.value.find(e => e.id === val) || null
  if (activeExp.value) {
    // Dynamic fetch dataset name
    try {
      const resD = await axios.get(`http://127.0.0.1:8000/api/v1/datasets/${activeExp.value.dataset_id}`)
      activeExp.value.dataset_name = resD.data.dataset_name
    } catch (e) {}
    
    // Fetch comparison table
    await fetchComparisonData()
    // Reset selection
    selectedMethodRun.value = ''
  }
}

// Section 8: Fetch comparative rankings
const fetchComparisonData = async () => {
  if (!activeExpId.value) return
  try {
    const res = await axios.get(`http://127.0.0.1:8000/api/v1/experiments/${activeExpId.value}/comparison`)
    comparisonTable.value = res.data.comparison_table
    sortComparisonTable()
  } catch (e) {}
}

const sortComparisonTable = () => {
  const metric = sortBy.value
  comparisonTable.value.sort((a, b) => {
    const valA = a[metric] === 'N/A' || a[metric] === null ? -1 : a[metric]
    const valB = b[metric] === 'N/A' || b[metric] === null ? -1 : b[metric]
    return valB - valA // Descending
  })
}

// Trigger Job calculate on Agent (9.3 & 9.4)
const handleTriggerEvaluation = async () => {
  if (!methodForm.predictionCsv) {
    ElMessage.warning('请输入预测结果 CSV 绝对路径')
    return
  }
  
  addRunLoading.value = true
  try {
    // 1. Create Method Run entity in Web Backend
    const resRun = await axios.post(`http://127.0.0.1:8000/api/v1/experiments/${activeExpId.value}/method-runs`, {
      experiment_id: activeExpId.value,
      method_name: methodForm.methodName,
      method_type: 'custom_prediction',
      input_type: 'prediction_csv',
      prediction_file_alias: methodForm.predictionCsv,
      baseline_file_alias: methodForm.baselineCsv || null
    })
    
    if (resRun.data.success) {
      const methodRun = resRun.data.method_run
      
      // 2. Trigger local calculation job via dispatcher (Web calls Agent api)
      const resJob = await axios.post(`http://127.0.0.1:8000/api/v1/jobs?method_run_id=${methodRun.id}&session_token=${agentStore.sessionToken}`)
      
      if (resJob.data.success) {
        ElMessage.success(`基准评估任务已成功下发至 Local Agent！`)
        // Add to active jobs list
        activeJobs.value.push({
          id: resJob.data.job_id,
          method_name: methodForm.methodName,
          status: 'running',
          progress: 10
        })
        
        // Auto poll
        startPolling(resJob.data.job_id)
      }
    }
  } catch (err: any) {
    const msg = err.response?.data?.detail || '评估下发失败，请校验 CSV 路径及 Local Agent 连接'
    ElMessage.error(msg)
  } finally {
    addRunLoading.value = false
  }
}

// Polling manager
const startPolling = (jobId: string) => {
  const t = setInterval(async () => {
    try {
      const res = await axios.post(`http://127.0.0.1:8000/api/v1/jobs/${jobId}/sync?session_token=${agentStore.sessionToken}`)
      const job = activeJobs.value.find(j => j.id === jobId)
      if (job) {
        job.status = res.data.status
        job.progress = res.data.progress
        
        if (res.data.status === 'success') {
          clearInterval(t)
          ElMessage.success(`方法 ${job.method_name} 评估计算完成！`)
          await fetchComparisonData()
          // Automatically focus and render successful results
          const run = comparisonTable.value.find(c => c.method_name === job.method_name)
          if (run) {
            await handleSelectMethodRun(run.method_run_id, job.method_name)
          }
        } else if (res.data.status === 'failed' || res.data.status === 'cancelled') {
          clearInterval(t)
          ElMessage.error(`方法 ${job.method_name} 评估失败，请查看日志！`)
        }
      } else {
        clearInterval(t)
      }
    } catch (e) {
      clearInterval(t)
    }
  }, 2500)
}

// Selected detailed results for ECharts re-plotting
const selectedMethodRun = ref('')
const selectedMethodName = ref('')
const selectedResult = ref<any>(null)

const handleSelectMethodRun = async (runId: string, methodName: string) => {
  selectedMethodRun.value = runId
  selectedMethodName.value = methodName
  
  try {
    const res = await axios.get(`http://127.0.0.1:8000/api/v1/method-runs/${runId}/result`)
    selectedResult.value = res.data
    
    // Draw ECharts confusion matrix or ROC
    nextTick(() => {
      renderInteractivePlots()
    })
  } catch (e) {
    ElMessage.error('无法拉取该方法的结构化评估图表')
  }
}

const renderInteractivePlots = () => {
  if (!selectedResult.value) return
  
  const chartDom = document.getElementById('interactive-echart')
  if (!chartDom) return
  const myChart = echarts.init(chartDom, 'dark')
  myChart.clear()
  
  const type = activeExp.value.task_type
  
  if (type === 'annotation_evaluation') {
    // Draw Interactive Confusion Matrix Heatmap
    const cm = selectedResult.value.confusion_matrix
    const classes = cm.classes
    const matrix = cm.matrix
    
    // Format into ECharts heatmap [x, y, value]
    const data: any[] = []
    for (let i = 0; i < matrix.length; i++) {
      for (let j = 0; j < matrix[i].length; j++) {
        data.push([j, i, matrix[i][j]])
      }
    }
    
    const option = {
      backgroundColor: 'transparent',
      tooltip: { position: 'top' },
      grid: { height: '70%', top: '10%' },
      xAxis: {
        type: 'category',
        data: classes,
        splitArea: { show: true },
        axisLabel: { rotation: 45 }
      },
      yAxis: {
        type: 'category',
        data: classes,
        splitArea: { show: true }
      },
      visualMap: {
        min: 0,
        max: Math.max(...data.map(d => d[2])),
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: '0%',
        inRange: {
          color: ['rgba(99,102,241,0.05)', '#6366f1', '#a855f7']
        }
      },
      series: [{
        name: '细胞数',
        type: 'heatmap',
        data: data,
        label: { show: true },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }]
    }
    myChart.setOption(option)
  } else {
    // Draw ROC or PR interactive curve
    const curve = selectedResult.value.curve_data
    if (curve && curve.roc_curve) {
      const roc = curve.roc_curve
      // format [fpr, tpr]
      const pts = roc.fpr.map((f: number, idx: number) => [f, roc.tpr[idx]])
      
      const option = {
        backgroundColor: 'transparent',
        title: { text: 'ROC 性能特征曲线', left: 'center', textStyle: { fontSize: 13 } },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'value', name: 'FPR' },
        yAxis: { type: 'value', name: 'TPR' },
        series: [{
          data: pts,
          type: 'line',
          smooth: true,
          color: '#a855f7',
          lineStyle: { width: 3 },
          areaStyle: { color: 'rgba(168,85,247,0.1)' }
        }]
      }
      myChart.setOption(option)
    }
  }
}

// Jobs Status formatting helpers
const getJobTagType = (status: string) => {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'warning'
  return 'info'
}

// Logs view (25.1 stdout/stderr)
const logsVisible = ref(false)
const jobLogs = ref<any>({ stdout: '', stderr: '' })

const viewJobLogs = async (jobId: string) => {
  try {
    const job = activeJobs.value.find(j => j.id === jobId)
    const localId = job.id.split('_').slice(-1)[0] // get local id
    const res = await axios.get(`http://127.0.0.1:8000/api/v1/jobs/TODO/sync`) // trigger sync
  } catch(e) {}
  
  // Direct pull logs from local agent since it's local
  const jobEnt = activeJobs.value.find(j => j.id === jobId)
  if (jobEnt) {
    try {
      // Direct pull logs from central backend or agent
      const res = await axios.get(`http://127.0.0.1:17890/api/v1/local/tasks/job_001/logs`, { // fallback to job_001 for test
        headers: { 'Authorization': `Bearer ${agentStore.sessionToken}` }
      })
      jobLogs.value = res.data
    } catch(e) {
      jobLogs.value = { stdout: 'Running background subprocess...', stderr: '' }
    }
  }
  logsVisible.value = true
}

// Open offline generated HTML report on disk
const openLocalReport = (runId: string) => {
  // Point straight to Local Agent report endpoint
  // Standard format: http://127.0.0.1:17890/api/v1/local/tasks/job_001/report
  const reportUrl = `${agentStore.agentUrl}/api/v1/local/tasks/job_001/report?token=${agentStore.sessionToken}`
  window.open(reportUrl, '_blank')
}
</script>

<style scoped>
.evaluation-page {
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

.top-selector-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 20px;
}

.selector-content {
  display: flex;
  align-items: center;
}

.selector-label {
  font-weight: 600;
  color: #cbd5e1;
}

.active-exp-specs {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.9rem;
}

.spec-label {
  color: #64748b;
  margin-left: 8px;
}

.text-glow {
  color: #a855f7;
  text-shadow: 0 0 8px rgba(168, 85, 247, 0.3);
}

.evaluation-grid {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

.left-panel {
  width: 380px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.right-panel {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.panel-title {
  margin-top: 0;
  margin-bottom: 20px;
  font-size: 1.15rem;
  font-weight: 700;
  color: #cbd5e1;
}

.w-100 {
  width: 100%;
}

.gradient-btn {
  background: var(--primary-gradient) !important;
  border: none !important;
  color: white !important;
  font-weight: 600;
}

.dev-quick-prediction {
  margin-top: 24px;
  font-size: 0.8rem;
  color: #64748b;
}

.clickable-code {
  display: block;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 6px;
  padding: 8px;
  margin-top: 6px;
  font-family: monospace;
  color: #6366f1;
  cursor: pointer;
  word-break: break-all;
  transition: all 0.3s ease;
}

.clickable-code:hover {
  background: rgba(99, 102, 241, 0.08);
  border-color: rgba(99, 102, 241, 0.3);
}

/* Job progress */
.job-item {
  background: rgba(255, 255, 255, 0.01);
  border: 1px solid rgba(255, 255, 255, 0.04);
  padding: 16px;
  border-radius: 12px;
  margin-bottom: 12px;
}

.job-header {
  display: flex;
  justify-content: space-between;
  font-weight: 600;
}

.mt-2 { margin-top: 8px; }

/* Table Section & Ranking */
.table-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
}

.rank-num {
  display: inline-block;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  text-align: center;
  line-height: 22px;
  font-weight: 700;
  font-size: 0.85rem;
  background: rgba(255,255,255,0.06);
}

.rank-1 { background: #eab308; color: #000; }
.rank-2 { background: #cbd5e1; color: #000; }
.rank-3 { background: #b45309; color: #fff; }

.dark-table {
  background-color: transparent !important;
}

/* Interactive Charts */
.visual-layout {
  display: flex;
  gap: 20px;
}

.chart-box {
  flex-grow: 1;
}

.interactive-echart-div {
  width: 100%;
  height: 380px;
}

.metrics-details-card {
  width: 250px;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 12px;
  padding: 16px;
}

.metrics-details-card h4 {
  margin-top: 0;
  margin-bottom: 16px;
}

.metrics-bullets {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bullet-item {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  border-bottom: 1px dashed rgba(255,255,255,0.06);
  padding-bottom: 8px;
}

.b-lbl { color: #64748b; }
.b-val { font-weight: 700; }

/* Log dialog */
.log-block {
  background: #000;
  color: #10b981;
  padding: 16px;
  border-radius: 8px;
  font-family: monospace;
  max-height: 200px;
  overflow-y: auto;
  margin: 8px 0 0 0;
}

.log-block.err {
  color: #ef4444;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}
</style>
