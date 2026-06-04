<template>
  <div class="datasets-page">
    <div class="main-layout">
      <!-- Left card: Path & registration -->
      <div class="left-col glass-card">
        <h3 class="section-title">📂 导入与注册本地数据集</h3>
        
        <el-form :model="form" label-position="top">
          <el-form-item label="本地 H5AD 绝对路径" required>
            <el-input 
              v-model="form.filepath" 
              placeholder="例如: C:\data\immune.h5ad" 
              class="neon-input"
            />
          </el-form-item>
          
          <el-button 
            type="primary" 
            class="gradient-btn w-100" 
            :disabled="!agentStore.paired" 
            :loading="inspectLoading"
            @click="handleInspectFile"
          >
            检测 H5AD 数据结构
          </el-button>
          
          <!-- Column bindings (appears after inspection success) -->
          <div v-if="inspectResult" class="col-bindings">
            <el-divider>选择标签与批次字段</el-divider>
            
            <div class="header-specs">
              <p>🧬 细胞数: <strong>{{ inspectResult.n_cells }}</strong> | 基因数: <strong>{{ inspectResult.n_genes }}</strong></p>
            </div>
            
            <el-form-item label="数据集重命名 (Alias)" required>
              <el-input v-model="form.datasetName" placeholder="例如: Immune_DC_2026" class="neon-input" />
            </el-form-item>
            
            <el-form-item label="真实细胞类型注释列 (label_col)" required>
              <el-select v-model="form.labelCol" placeholder="请选择主标签字段" class="w-100 neon-select">
                <el-option v-for="col in inspectResult.obs_columns" :key="col" :label="col" :value="col" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="实验批次来源列 (batch_col) 可选">
              <el-select v-model="form.batchCol" placeholder="请选择批次字段" clearable class="w-100 neon-select">
                <el-option v-for="col in inspectResult.obs_columns" :key="col" :label="col" :value="col" />
              </el-select>
            </el-form-item>

            <el-form-item label="稀有细胞定义阈值">
              <el-slider v-model="form.rareThreshold" :min="1" :max="10" :format-tooltip="(val: number) => val + '%'" />
              <span class="slider-desc">占比低于该阈值的细胞类型将被判定为稀有细胞候选类</span>
            </el-form-item>
            
            <el-button 
              type="success" 
              class="w-100 register-btn" 
              :loading="registerLoading"
              @click="handleRegisterDataset"
            >
              分析标签分布并注册数据集
            </el-button>
          </div>
        </el-form>
        
        <div class="test-helper" v-if="agentStore.paired">
          <el-divider>快速测试指引</el-divider>
          <p class="helper-text">
            若本地无可用单细胞数据，可使用此测试路径，系统已在本地准备好 tiny 数据集：
            <br />
            <code class="clickable-code" @click="form.filepath = mockPath">{{ mockPath }}</code>
          </p>
        </div>
      </div>

      <!-- Right card: Visualizations and stats -->
      <div class="right-col glass-card" v-if="registeredData">
        <h3 class="section-title">📊 数据集概览: {{ registeredData.dataset_name }}</h3>
        
        <div class="meta-row">
          <div class="meta-badge">🧬 细胞数: {{ registeredData.summary.n_cells }}</div>
          <div class="meta-badge">🧬 基因数: {{ registeredData.summary.n_genes }}</div>
          <div class="meta-badge">🧪 有效标签细胞: {{ registeredData.summary.valid_label_cells }}</div>
          <div class="meta-badge warning">⚠️ 无效/缺失细胞: {{ registeredData.summary.invalid_label_cells }} ({{ (registeredData.summary.invalid_label_ratio * 100).toFixed(2) }}%)</div>
        </div>

        <el-divider />

        <!-- Chart layout -->
        <div class="charts-container">
          <div class="chart-box">
            <h4>🏷️ 细胞类型分布前十类统计</h4>
            <div id="labels-chart" class="echart-div"></div>
          </div>
        </div>

        <el-divider />

        <!-- Rare Candidates Table -->
        <h4 class="sub-title">🦄 自动筛选的稀有细胞类型候选</h4>
        <p class="table-desc">基于您设定的稀有定义阈值 ({{ form.rareThreshold }}%)，检测到以下稀有细胞类：</p>
        
        <el-table :data="registeredData.summary.rare_candidates" style="width: 100%" size="small" class="dark-table">
          <el-table-column prop="class_name" label="细胞类型" />
          <el-table-column prop="count" label="细胞数">
            <template #default="scope">
              <el-tag type="info" size="small">{{ scope.row.count }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="ratio" label="所占比例">
            <template #default="scope">
              <strong>{{ (scope.row.ratio * 100).toFixed(2) }}%</strong>
            </template>
          </el-table-column>
        </el-table>
      </div>
      
      <!-- Empty panel -->
      <div class="right-col glass-card empty-state" v-else>
        <el-empty description="请输入 H5AD 绝对路径，进行细胞层面的元数据探查与标签分布可视化分析" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, nextTick, onMounted } from 'vue'
import { useAgentStore } from '../stores/agent'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import * as echarts from 'echarts'

const agentStore = useAgentStore()
const inspectLoading = ref(false)
const registerLoading = ref(false)

const inspectResult = ref<any>(null)
const registeredData = ref<any>(null)

// Standard workspace paths for user convenience
const mockPath = ref('')
onMounted(() => {
  // Try to locate mock dataset path under local-agent
  // Use the real pancreas dataset on macOS; tiny dataset as fallback
  const isWindows = navigator.platform.toLowerCase().includes('win')
  mockPath.value = isWindows
    ? 'C:\\Users\\username\\Desktop\\scAnnoRare\\data\\pancreas_baron.h5ad'
    : '/Users/wangxiansheng/Desktop/scAnnoRare/data/pancreas_baron.h5ad'
})

const form = reactive({
  filepath: '',
  datasetName: 'Immune_DC_Evaluation',
  labelCol: '',
  batchCol: '',
  rareThreshold: 5
})

const handleInspectFile = async () => {
  if (!form.filepath) {
    ElMessage.warning('请输入 H5AD 文件绝对路径')
    return
  }
  
  inspectLoading.value = true
  inspectResult.value = null
  
  try {
    const res = await axios.post(`${agentStore.agentUrl}/api/v1/local/files/select`, {
      filepath: form.filepath
    }, {
      headers: {
        'Authorization': `Bearer ${agentStore.sessionToken}`
      }
    })
    
    if (res.data.success) {
      inspectResult.value = res.data
      ElMessage.success('成功解析 H5AD 文件头，已加载字段列！')
    }
  } catch (err: any) {
    const msg = err.response?.data?.detail || 'H5AD 解析失败，请确认文件路径及 anndata 包状态'
    ElMessage.error(msg)
  } finally {
    inspectLoading.value = false
  }
}

// Draw ECharts Distribution
const renderCharts = () => {
  if (!registeredData.value) return
  
  const dist = registeredData.value.summary.label_distribution
  const sortedLabels = Object.entries(dist)
    .sort((a: any, b: any) => b[1].count - a[1].count)
    .slice(0, 10) // top 10

  const categories = sortedLabels.map(item => item[0]).reverse()
  const counts = sortedLabels.map((item: any) => item[1].count).reverse()
  
  const chartDom = document.getElementById('labels-chart')
  if (!chartDom) return
  
  const myChart = echarts.init(chartDom, 'dark')
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: '3%',
      right: '8%',
      bottom: '3%',
      top: '5%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }
    },
    yAxis: {
      type: 'category',
      data: categories,
      axisLabel: { color: '#cbd5e1' }
    },
    series: [
      {
        name: '细胞数',
        type: 'bar',
        data: counts,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#6366f1' },
            { offset: 1, color: '#a855f7' }
          ]),
          borderRadius: [0, 4, 4, 0]
        }
      }
    ]
  }
  myChart.setOption(option)
}

const handleRegisterDataset = async () => {
  if (!form.labelCol) {
    ElMessage.warning('请选择真实细胞类型字段')
    return
  }
  
  registerLoading.value = true
  try {
    // 1. Ask local agent to count label distribution and extract rare candidates
    const resAgent = await axios.post(`${agentStore.agentUrl}/api/v1/local/files/register-dataset`, {
      filepath: form.filepath,
      dataset_name: form.datasetName,
      label_col: form.labelCol,
      batch_col: form.batchCol || null,
      rare_threshold: form.rareThreshold / 100
    }, {
      headers: {
        'Authorization': `Bearer ${agentStore.sessionToken}`
      }
    })
    
    if (resAgent.data.success) {
      const summary = resAgent.data.summary
      
      // 2. Synchronize to central Web Backend database
      const resWeb = await axios.post('http://127.0.0.1:8000/api/v1/datasets', {
        project_id: null,
        dataset_name: form.datasetName,
        local_dataset_alias: form.filepath,
        label_col: form.labelCol || null,
        batch_col: form.batchCol || null,
        n_cells: summary.n_cells,
        n_genes: summary.n_genes,
        obs_columns: inspectResult.value.obs_columns,
        var_columns: inspectResult.value.var_columns,
        label_distribution: summary.label_distribution,
        rare_candidates: summary.rare_candidates
      })
      
      if (resWeb.data.success) {
        registeredData.value = resAgent.data
        ElMessage.success('标签结构分析成功，数据集已在平台注册！')
        
        // Wait DOM render, then plot
        nextTick(() => {
          renderCharts()
        })
      }
    }
  } catch (err: any) {
    const msg = err.response?.data?.detail || '数据集注册失败'
    ElMessage.error(msg)
  } finally {
    registerLoading.value = false
  }
}
</script>

<style scoped>
.datasets-page {
  display: flex;
  flex-direction: column;
}

.glass-card {
  background: rgba(22, 28, 36, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
}

.main-layout {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

.left-col {
  width: 380px;
  flex-shrink: 0;
}

.right-col {
  flex-grow: 1;
}

.section-title {
  margin-top: 0;
  margin-bottom: 20px;
  font-size: 1.15rem;
  font-weight: 700;
  color: #cbd5e1;
}

.neon-input :deep(.el-input__wrapper) {
  background-color: rgba(255, 255, 255, 0.02) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  box-shadow: none !important;
}

.neon-input :deep(.el-input__wrapper):hover,
.neon-input :deep(.el-input__wrapper).is-focus {
  border-color: var(--primary-color) !important;
  box-shadow: 0 0 8px rgba(99, 102, 241, 0.3) !important;
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

.col-bindings {
  margin-top: 24px;
}

.header-specs {
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 16px;
  text-align: center;
  font-size: 0.85rem;
}

.slider-desc {
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 4px;
  display: block;
}

.register-btn {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
  border: none !important;
  font-weight: 600;
}

.test-helper {
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
  color: #a855f7;
  cursor: pointer;
  word-break: break-all;
  transition: all 0.3s ease;
}

.clickable-code:hover {
  background: rgba(168, 85, 247, 0.08);
  border-color: rgba(168, 85, 247, 0.3);
}

/* Right col components */
.meta-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.meta-badge {
  padding: 6px 12px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 0.85rem;
  font-weight: 600;
}

.meta-badge.warning {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.charts-container {
  margin: 20px 0;
}

.chart-box h4 {
  margin-top: 0;
  margin-bottom: 16px;
  color: #cbd5e1;
}

.echart-div {
  width: 100%;
  height: 250px;
}

.dark-table {
  background-color: transparent !important;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}
</style>
