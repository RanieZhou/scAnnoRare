<template>
  <div class="experiments-page">
    <div class="main-layout">
      <!-- Left side: Configuration form -->
      <div class="left-col glass-card">
        <h3 class="section-title">🧪 建立基准评估实验主题</h3>
        
        <el-form :model="form" label-position="top">
          <!-- Select Dataset -->
          <el-form-item label="选择基准数据集" required>
            <el-select 
              v-model="form.datasetId" 
              placeholder="选择已注册的数据集" 
              class="w-100 neon-select"
              @change="handleDatasetChange"
            >
              <el-option v-for="d in datasets" :key="d.id" :label="d.dataset_name" :value="d.id" />
            </el-select>
          </el-form-item>

          <div v-if="selectedDataset" class="dataset-info-box">
            <p>📊 细胞数: <strong>{{ selectedDataset.n_cells }}</strong> | 注释列: <strong>{{ selectedDataset.label_col }}</strong></p>
          </div>

          <el-form-item label="基准实验名称 (Experiment Name)" required>
            <el-input v-model="form.experimentName" placeholder="例如: immune_rare_cell_benchmark_v1" class="neon-input" />
          </el-form-item>

          <!-- Select Task Type -->
          <el-form-item label="评估任务主要维度" required>
            <el-radio-group v-model="form.taskType" class="neon-radio-group">
              <el-radio-button label="annotation_evaluation">细胞类型注释评估</el-radio-button>
              <el-radio-button label="rare_detection_evaluation">稀有细胞识别评估</el-radio-button>
            </el-radio-group>
          </el-form-item>

          <!-- Rare Detection Configurations -->
          <div v-if="form.taskType === 'rare_detection_evaluation' && selectedDataset" class="rare-options">
            <el-divider>稀有细胞专门设置</el-divider>
            
            <el-form-item label="稀有评估模式 (Rare Mode)" required>
              <el-select v-model="form.rareMode" placeholder="选择评估模式" class="w-100 neon-select">
                <el-option value="single_rare" label="Single Rare (指定单一种类评估)" />
                <el-option value="multi_rare_per_class" label="Multi Rare Per Class (各稀有类独立 One-vs-Rest 评估)" />
                <el-option value="pooled_rare_vs_nonrare" label="Pooled Rare vs Non-Rare (全部稀有类合并正样本评估)" />
              </el-select>
            </el-form-item>

            <el-form-item label="目标稀有细胞类型 (Target Classes)" required>
              <el-select 
                v-model="form.targetRareClasses" 
                placeholder="请选择评估的目标稀有类" 
                multiple 
                collapse-tags 
                class="w-100 neon-select"
              >
                <!-- list from selected dataset's rare candidates -->
                <el-option 
                  v-for="item in selectedDataset.rare_candidates" 
                  :key="item.class_name" 
                  :label="`${item.class_name} (占 ${(item.ratio * 100).toFixed(2)}%)`" 
                  :value="item.class_name" 
                />
              </el-select>
              <span class="sub-desc">仅展示占比在 {{ (selectedDataset.rare_candidates?.[0]?.ratio || 0.05) * 100 }}% 以下的候选细胞类</span>
            </el-form-item>
          </div>

          <el-button 
            type="primary" 
            class="gradient-btn w-100 submit-btn" 
            :loading="createLoading"
            @click="handleCreateExperiment"
          >
            发布实验基准配置
          </el-button>
        </el-form>
      </div>

      <!-- Right side: Configured Experiments list -->
      <div class="right-col glass-card">
        <h3 class="section-title">📋 平台活跃实验主题列表</h3>
        
        <el-table :data="experiments" style="width: 100%" size="small" class="dark-table">
          <el-table-column prop="experiment_name" label="实验名称" min-width="150" />
          <el-table-column prop="task_type" label="评估类型">
            <template #default="scope">
              <el-tag :type="scope.row.task_type === 'annotation_evaluation' ? 'success' : 'warning'" size="small">
                {{ scope.row.task_type === 'annotation_evaluation' ? '注释精度' : '稀有细胞检测' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="label_col" label="绑定标签列" />
          <el-table-column label="具体配置" min-width="180">
            <template #default="scope">
              <div v-if="scope.row.task_type === 'rare_detection_evaluation'" class="spec-tags">
                <el-tag type="info" size="small" effect="plain">{{ scope.row.rare_mode }}</el-tag>
                <el-tag 
                  v-for="cls in scope.row.target_rare_classes" 
                  :key="cls" 
                  type="danger" 
                  size="small" 
                  class="ml-1"
                >
                  {{ cls }}
                </el-tag>
              </div>
              <span v-else class="text-muted">标准细胞多分类混淆矩阵指标</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const datasets = ref<any[]>([])
const experiments = ref<any[]>([])
const selectedDataset = ref<any>(null)
const createLoading = ref(false)

const form = reactive({
  datasetId: '',
  experimentName: 'Immune_Rare_Cell_Benchmark_1',
  taskType: 'annotation_evaluation',
  rareMode: 'pooled_rare_vs_nonrare',
  targetRareClasses: [] as string[]
})

const fetchDatasets = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/v1/datasets')
    datasets.value = res.data
  } catch (e) {
    console.error('Failed to get datasets from web backend.')
  }
}

const fetchExperiments = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/v1/experiments')
    experiments.value = res.data
  } catch (e) {
    console.error('Failed to get experiments.')
  }
}

onMounted(() => {
  fetchDatasets()
  fetchExperiments()
})

const handleDatasetChange = (val: string) => {
  selectedDataset.value = datasets.value.find(d => d.id === val) || null
  if (selectedDataset.value) {
    form.targetRareClasses = []
  }
}

const handleCreateExperiment = async () => {
  if (!form.datasetId) {
    ElMessage.warning('请选择基准数据集')
    return
  }
  if (!form.experimentName) {
    ElMessage.warning('请输入实验名称')
    return
  }
  
  if (form.taskType === 'rare_detection_evaluation' && form.targetRareClasses.length === 0) {
    ElMessage.warning('请选择目标稀有细胞类型')
    return
  }
  
  createLoading.value = true
  try {
    const res = await axios.post('http://127.0.0.1:8000/api/v1/experiments', {
      project_id: null,
      dataset_id: form.datasetId,
      experiment_name: form.experimentName,
      task_type: form.taskType,
      label_col: selectedDataset.value.label_col,
      batch_col: selectedDataset.value.batch_col || null,
      rare_mode: form.taskType === 'rare_detection_evaluation' ? form.rareMode : null,
      rare_threshold: 0.05, // default
      target_rare_classes: form.taskType === 'rare_detection_evaluation' ? form.targetRareClasses : null
    })
    
    if (res.data.success) {
      ElMessage.success('基准评估实验发布成功！')
      fetchExperiments()
      // Reset
      form.experimentName = 'Immune_Rare_Cell_Benchmark_' + (experiments.value.length + 2)
      form.targetRareClasses = []
    }
  } catch (err) {
    ElMessage.error('创建实验主题失败')
  } finally {
    createLoading.value = false
  }
}
</script>

<style scoped>
.experiments-page {
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
  width: 400px;
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

.dataset-info-box {
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 16px;
  text-align: center;
  font-size: 0.85rem;
}

.w-100 {
  width: 100%;
}

.neon-input :deep(.el-input__wrapper) {
  background-color: rgba(255, 255, 255, 0.02) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  box-shadow: none !important;
}

.gradient-btn {
  background: var(--primary-gradient) !important;
  border: none !important;
  color: white !important;
  font-weight: 600;
  margin-top: 16px;
}

.sub-desc {
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 4px;
  display: block;
}

.ml-1 {
  margin-left: 4px;
}

.spec-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.dark-table {
  background-color: transparent !important;
}
</style>
