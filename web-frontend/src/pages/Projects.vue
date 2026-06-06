<template>
  <div class="projects-page">
    <div class="main-layout">
      <!-- 左：创建项目 -->
      <div class="left-col glass-card">
        <h3 class="section-title">🗂 新建研究项目</h3>
        <p class="hint">项目用于组织你的数据集与实验，例如「胰腺稀有细胞基准」。</p>
        <el-form :model="form" label-position="top">
          <el-form-item label="项目名称" required>
            <el-input v-model="form.project_name" placeholder="例如：pancreas rare cell benchmark" class="neon-input" />
          </el-form-item>
          <el-form-item label="项目描述">
            <el-input v-model="form.description" type="textarea" :rows="3" placeholder="可选" class="neon-input" />
          </el-form-item>
          <el-button type="primary" class="gradient-btn w-100" :loading="creating" @click="createProject">
            创建项目
          </el-button>
        </el-form>
      </div>

      <!-- 右：项目列表 -->
      <div class="right-col glass-card">
        <div class="list-header">
          <h3 class="section-title">📋 我的项目（{{ projects.length }}）</h3>
          <el-button size="small" plain @click="fetchProjects">刷新</el-button>
        </div>
        <el-empty v-if="!loading && projects.length === 0" description="还没有项目，先在左侧创建一个" />
        <div v-else class="proj-list">
          <div v-for="p in projects" :key="p.id" class="proj-card">
            <div class="proj-main">
              <div class="proj-name">{{ p.project_name }}</div>
              <div class="proj-desc">{{ p.description || '（无描述）' }}</div>
              <div class="proj-time">创建于 {{ fmt(p.created_at) }}</div>
            </div>
            <el-popconfirm title="确认删除该项目？其下数据集/实验也会被级联删除。" @confirm="removeProject(p.id)">
              <template #reference>
                <el-button size="small" type="danger" plain>删除</el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const WEB = 'http://127.0.0.1:8000'
const loading = ref(false)
const creating = ref(false)
const projects = ref<any[]>([])
const form = reactive({ project_name: '', description: '' })

async function fetchProjects() {
  loading.value = true
  try {
    const res = await axios.get(`${WEB}/api/v1/projects`)
    projects.value = res.data.items || []
  } catch (_) {
    ElMessage.error('无法加载项目列表')
  } finally {
    loading.value = false
  }
}

async function createProject() {
  if (!form.project_name.trim()) {
    ElMessage.warning('请输入项目名称')
    return
  }
  creating.value = true
  try {
    await axios.post(`${WEB}/api/v1/projects`, {
      project_name: form.project_name,
      description: form.description || null,
    })
    ElMessage.success('项目已创建')
    form.project_name = ''
    form.description = ''
    await fetchProjects()
  } catch (_) {
    ElMessage.error('创建失败')
  } finally {
    creating.value = false
  }
}

async function removeProject(id: string) {
  try {
    await axios.delete(`${WEB}/api/v1/projects/${id}`)
    ElMessage.success('已删除')
    await fetchProjects()
  } catch (_) {
    ElMessage.error('删除失败')
  }
}

function fmt(ts: number) {
  return ts ? new Date(ts * 1000).toLocaleString('zh-CN') : ''
}

onMounted(fetchProjects)
</script>

<style scoped>
.projects-page { display: flex; flex-direction: column; gap: 24px; }
.glass-card {
  background: rgba(22, 28, 36, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}
.main-layout { display: flex; gap: 24px; align-items: flex-start; }
.left-col { width: 380px; flex-shrink: 0; }
.right-col { flex: 1; }
.section-title { margin: 0 0 12px; font-size: 1.1rem; font-weight: 700; color: #cbd5e1; }
.hint { font-size: 0.82rem; color: #64748b; margin: 0 0 16px; }
.w-100 { width: 100%; }
.gradient-btn { background: linear-gradient(135deg, #6366f1, #a855f7) !important; border: none !important; color: #fff !important; font-weight: 600; }
.list-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.proj-list { display: flex; flex-direction: column; gap: 12px; }
.proj-card {
  display: flex; justify-content: space-between; align-items: center;
  background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px; padding: 16px;
}
.proj-name { font-size: 1.02rem; font-weight: 700; color: #f1f5f9; }
.proj-desc { font-size: 0.85rem; color: #94a3b8; margin-top: 4px; }
.proj-time { font-size: 0.75rem; color: #475569; margin-top: 6px; }
</style>
