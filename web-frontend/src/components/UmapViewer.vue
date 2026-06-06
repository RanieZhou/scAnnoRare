<template>
  <div class="umap-viewer">
    <div class="umap-toolbar">
      <el-button type="primary" plain size="small" :loading="loading" :disabled="!agentStore.paired" @click="compute">
        🗺 计算并查看 UMAP 嵌入图
      </el-button>
      <span v-if="meta" class="umap-meta">
        {{ meta.n_points }} 点{{ meta.subsampled ? `（从 ${meta.n_total} 子采样）` : '' }} · {{ meta.classes }} 类
      </span>
      <span v-if="loading" class="umap-meta">UMAP 计算中，约需 10–30 秒…</span>
    </div>
    <div v-show="hasPlot" ref="chartEl" class="umap-canvas"></div>
    <el-empty v-if="!hasPlot && !loading" description="点击上方按钮，对该数据集计算 UMAP 二维嵌入并按细胞类型着色" :image-size="70" />
  </div>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { useAgentStore } from '../stores/agent'

const props = defineProps<{ filepath: string; labelCol: string }>()
const agentStore = useAgentStore()

const loading = ref(false)
const hasPlot = ref(false)
const chartEl = ref<HTMLElement | null>(null)
const meta = ref<{ n_points: number; n_total: number; subsampled: boolean; classes: number } | null>(null)
let chart: echarts.ECharts | null = null

async function compute() {
  if (!props.filepath || !props.labelCol) {
    ElMessage.warning('请先选择数据文件并指定标签列')
    return
  }
  loading.value = true
  hasPlot.value = false
  try {
    const H = { Authorization: `Bearer ${agentStore.sessionToken}` }
    const res = await axios.post(
      `${agentStore.agentUrl}/api/v1/local/tasks/compute-embedding`,
      { filepath: props.filepath, label_col: props.labelCol, max_cells: 4000 },
      { headers: H },
    )
    const jid = res.data.local_job_id
    // 轮询
    let result: any = null
    for (let i = 0; i < 90; i++) {
      await new Promise((r) => setTimeout(r, 1500))
      const s = await axios.get(`${agentStore.agentUrl}/api/v1/local/tasks/${jid}`, { headers: H })
      if (s.data.status === 'success') { result = s.data.result; break }
      if (s.data.status === 'failed') throw new Error('嵌入计算失败')
    }
    if (!result) throw new Error('计算超时')
    render(result)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || err.message || 'UMAP 计算失败')
  } finally {
    loading.value = false
  }
}

function render(data: any) {
  meta.value = { n_points: data.n_points, n_total: data.n_total, subsampled: data.subsampled, classes: data.classes.length }
  hasPlot.value = true

  // 按类别分组成多个 series（图例 + 配色）
  const byClass: Record<string, [number, number][]> = {}
  for (const c of data.classes) byClass[c] = []
  for (let i = 0; i < data.x.length; i++) {
    const lbl = data.label[i]
    if (!byClass[lbl]) byClass[lbl] = []
    byClass[lbl].push([data.x[i], data.y[i]])
  }
  const palette = [
    '#6366f1', '#a855f7', '#10b981', '#f59e0b', '#ef4444', '#3b82f6', '#ec4899',
    '#14b8a6', '#f97316', '#8b5cf6', '#22c55e', '#eab308', '#06b6d4', '#f43f5e',
    '#84cc16', '#d946ef', '#0ea5e9', '#fb7185',
  ]
  const series = data.classes.map((c: string, i: number) => ({
    name: c,
    type: 'scatter',
    symbolSize: 4,
    itemStyle: { color: palette[i % palette.length], opacity: 0.75 },
    data: byClass[c],
  }))

  if (!chart) chart = echarts.init(chartEl.value!, 'dark')
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: (p: any) => `${p.seriesName}<br/>(${(p.value[0] as number).toFixed(2)}, ${(p.value[1] as number).toFixed(2)})` },
    legend: {
      type: 'scroll',
      orient: 'horizontal',
      bottom: 0,
      left: 'center',
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { color: '#94a3b8', fontSize: 10 },
      pageTextStyle: { color: '#94a3b8' },
      pageIconColor: '#94a3b8',
      pageIconInactiveColor: '#4a5568',
    },
    grid: { left: 50, right: 20, top: 20, bottom: 90 },
    xAxis: { name: 'UMAP-1', scale: true, axisLabel: { color: '#64748b' }, splitLine: { show: false } },
    yAxis: { name: 'UMAP-2', scale: true, axisLabel: { color: '#64748b' }, splitLine: { show: false } },
    series,
  }, true)
}

onBeforeUnmount(() => { chart?.dispose() })
</script>

<style scoped>
.umap-viewer { display: flex; flex-direction: column; gap: 12px; }
.umap-toolbar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.umap-meta { font-size: 0.8rem; color: #64748b; }
.umap-canvas { width: 100%; height: 520px; }
</style>
