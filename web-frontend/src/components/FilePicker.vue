<template>
  <el-dialog
    :model-value="modelValue"
    :title="title"
    width="640px"
    class="dark-dialog file-picker"
    @update:model-value="$emit('update:modelValue', $event)"
    @open="onOpen"
  >
    <!-- 当前路径 -->
    <div class="path-bar">
      <el-button size="small" :disabled="!parent" @click="go(parent)" text>
        ⬆ 上级
      </el-button>
      <el-button size="small" @click="go(home)" text>🏠 主目录</el-button>
      <el-button size="small" @click="go('__drives__')" text>💾 所有磁盘</el-button>
      <code class="cur-path">{{ current === '__drives__' ? '所有磁盘' : (current || '—') }}</code>
    </div>

    <div v-loading="loading" class="listing">
      <el-empty v-if="!loading && dirs.length === 0 && files.length === 0"
                description="此目录下没有可选文件" :image-size="60" />

      <!-- 目录 -->
      <div v-for="d in dirs" :key="d.path" class="row dir" @click="go(d.path)">
        <span class="icon">{{ current === '__drives__' ? '💾' : '📁' }}</span><span class="name">{{ d.name }}</span>
      </div>
      <!-- 文件 -->
      <div
        v-for="f in files"
        :key="f.path"
        class="row file"
        :class="{ selected: selected === f.path }"
        @click="selected = f.path"
        @dblclick="confirm(f.path)"
      >
        <span class="icon">📄</span>
        <span class="name">{{ f.name }}</span>
        <span class="size">{{ fmtSize(f.size) }}</span>
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :disabled="!selected" @click="confirm(selected)">
        选择此文件
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAgentStore } from '../stores/agent'

const props = defineProps<{
  modelValue: boolean
  title?: string
  exts?: string // 例如 ".h5ad" 或 ".csv"
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'select', path: string): void
}>()

const agentStore = useAgentStore()
const title = props.title || '选择文件'

const loading = ref(false)
const current = ref('')
const parent = ref<string | null>(null)
const home = ref('')
const dirs = ref<any[]>([])
const files = ref<any[]>([])
const selected = ref('')

async function load(path?: string) {
  if (!agentStore.paired) {
    ElMessage.warning('请先配对本地 Agent')
    return
  }
  loading.value = true
  selected.value = ''
  try {
    const res = await axios.get(`${agentStore.agentUrl}/api/v1/local/files/browse`, {
      headers: { Authorization: `Bearer ${agentStore.sessionToken}` },
      params: { path, exts: props.exts },
    })
    current.value = res.data.current
    parent.value = res.data.parent
    home.value = res.data.home
    dirs.value = res.data.dirs
    files.value = res.data.files
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '无法读取目录')
  } finally {
    loading.value = false
  }
}

function onOpen() {
  load(current.value || undefined)
}
function go(path: string | null) {
  if (path) load(path)
}
function confirm(path: string) {
  if (!path) return
  emit('select', path)
  emit('update:modelValue', false)
}
function fmtSize(bytes: number) {
  if (bytes > 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + ' MB'
  if (bytes > 1024) return (bytes / 1024).toFixed(0) + ' KB'
  return bytes + ' B'
}
</script>

<style scoped>
.path-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.cur-path {
  flex: 1;
  font-size: 0.78rem;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.03);
  padding: 4px 8px;
  border-radius: 6px;
  word-break: break-all;
}
.listing {
  max-height: 360px;
  overflow-y: auto;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  min-height: 120px;
}
.row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 14px;
  cursor: pointer;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  font-size: 0.9rem;
}
.row:hover { background: rgba(99, 102, 241, 0.08); }
.row.selected { background: rgba(99, 102, 241, 0.18); }
.row .icon { font-size: 1rem; }
.row .name { flex: 1; color: #e6edf3; }
.row.dir .name { color: #c7d2fe; }
.row .size { font-size: 0.78rem; color: #64748b; }
</style>
