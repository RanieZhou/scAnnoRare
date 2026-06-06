<template>
  <div class="settings-page">
    <!-- 账号信息 -->
    <div class="glass-card">
      <h3 class="section-title">👤 账号信息</h3>
      <div class="info-grid">
        <div class="info-item"><span class="lbl">用户名</span><span class="val">{{ authStore.username }}</span></div>
        <div class="info-item"><span class="lbl">用户 ID</span><span class="val">{{ authStore.userId }}</span></div>
        <div class="info-item"><span class="lbl">登录令牌</span><span class="val mono">{{ tokenPreview }}</span></div>
      </div>
    </div>

    <!-- 修改密码 -->
    <div class="glass-card">
      <h3 class="section-title">🔒 修改密码</h3>
      <el-form :model="pwForm" label-position="top" style="max-width: 420px;">
        <el-form-item label="原密码">
          <el-input v-model="pwForm.old_password" type="password" show-password class="neon-input" />
        </el-form-item>
        <el-form-item label="新密码（至少 4 位）">
          <el-input v-model="pwForm.new_password" type="password" show-password class="neon-input" />
        </el-form-item>
        <el-button type="primary" class="gradient-btn" :loading="pwLoading" @click="changePassword">
          确认修改
        </el-button>
      </el-form>
    </div>

    <!-- 本地节点状态 -->
    <div class="glass-card">
      <h3 class="section-title">🖥️ 本地计算节点</h3>
      <div class="status-line">
        <span class="dot" :class="agentStore.isOnline ? 'on' : 'off'"></span>
        <span>{{ agentStore.isOnline ? '已连接（127.0.0.1:17890）' : '未连接' }}</span>
        <el-tag v-if="agentStore.paired" type="success" size="small" effect="dark">已配对</el-tag>
        <el-button size="small" plain @click="$router.push('/agent')">前往配对页</el-button>
      </div>
      <div v-if="agentStore.envInfo" class="info-grid mt">
        <div class="info-item"><span class="lbl">操作系统</span><span class="val">{{ agentStore.envInfo.os }}</span></div>
        <div class="info-item"><span class="lbl">Python</span><span class="val">v{{ agentStore.envInfo.python_version }}</span></div>
        <div class="info-item"><span class="lbl">CPU 核心</span><span class="val">{{ agentStore.envInfo.cpu_count }}</span></div>
        <div class="info-item"><span class="lbl">内存</span><span class="val">{{ agentStore.envInfo.memory_total_gb }} GB</span></div>
      </div>
    </div>

    <!-- Python 环境管理 -->
    <div class="glass-card">
      <h3 class="section-title">🐍 Python 环境管理</h3>
      <p class="helper">检测本地 conda / pyenv / system Python 环境，选定后可在评估页直接运行 scANVI 等重型方法（无需打包进 Agent）。</p>

      <div class="env-toolbar">
        <el-button size="small" type="primary" plain :loading="envScanning" :disabled="!agentStore.paired" @click="detectEnvs">
          🔍 重新扫描环境
        </el-button>
        <el-button size="small" plain :disabled="!agentStore.paired" @click="showProbeDialog = true">
          ➕ 手动添加路径
        </el-button>
        <span class="env-meta" v-if="envLastScan">上次扫描：{{ fmtTime(envLastScan) }}</span>
        <span class="env-meta scanning" v-if="envScanning">扫描中，请稍候…</span>
      </div>

      <div v-if="!agentStore.paired" class="env-empty">请先连接并配对本地 Agent</div>
      <div v-else-if="envs.length === 0 && !envScanning" class="env-empty">
        未检测到环境，点击「重新扫描」开始自动检测
      </div>

      <div v-else class="env-list">
        <div
          v-for="env in envs"
          :key="env.id"
          class="env-card"
          :class="{ 'env-default': env.python_path === defaultPythonPath }"
        >
          <div class="env-header">
            <span class="env-name">{{ env.name }}</span>
            <el-tag size="small" :type="envSourceType(env.source)" effect="dark">{{ env.source }}</el-tag>
            <el-tag v-if="env.python_path === defaultPythonPath" size="small" type="success" effect="dark">默认外部环境</el-tag>
          </div>
          <div class="env-path">{{ env.python_path }}</div>
          <div class="env-caps">
            <span class="cap-badge" v-for="(ver, pkg) in env.capabilities" :key="pkg"
              :class="ver ? 'cap-ok' : 'cap-miss'">
              {{ pkg }}{{ ver ? ' ✓' : ' ✗' }}
            </span>
          </div>
          <div class="env-actions">
            <el-button size="small" plain @click="setDefault(env.python_path)">设为默认</el-button>
            <el-button size="small" type="danger" plain @click="removeEnv(env.id)">移除</el-button>
          </div>
        </div>
      </div>

      <!-- 手动添加路径对话框 -->
      <el-dialog v-model="showProbeDialog" title="手动添加 Python 路径" width="480px" class="dark-dialog">
        <el-form label-position="top">
          <el-form-item label="Python 可执行文件路径">
            <el-input v-model="probePath" placeholder="例如 /opt/miniconda3/envs/sc-env/bin/python3" class="neon-input" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showProbeDialog = false">取消</el-button>
          <el-button type="primary" :loading="probeLoading" @click="probeEnv">探测并添加</el-button>
        </template>
      </el-dialog>
    </div>

    <!-- 关于 -->
    <div class="glass-card">
      <h3 class="section-title">ℹ️ 关于</h3>
      <p class="about">单细胞细胞类型注释与稀有细胞识别多方法评估系统</p>
      <p class="about-sub">scAnnoRare · 版本 V1.1</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useAgentStore } from '../stores/agent'

const WEB = 'http://127.0.0.1:8000'
const router = useRouter()
const authStore = useAuthStore()
const agentStore = useAgentStore()

const tokenPreview = computed(() => {
  const t = authStore.token || ''
  return t ? t.slice(0, 24) + '…' : '—'
})

const pwForm = reactive({ old_password: '', new_password: '' })
const pwLoading = ref(false)

async function changePassword() {
  if (!pwForm.old_password || !pwForm.new_password) {
    ElMessage.warning('请填写原密码和新密码')
    return
  }
  pwLoading.value = true
  try {
    await axios.post(`${WEB}/api/v1/auth/change-password`, { ...pwForm })
    ElMessage.success('密码已修改，请重新登录')
    authStore.logout()
    router.push('/login')
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '修改失败')
  } finally {
    pwLoading.value = false
  }
}

// ── Python 环境管理 ────────────────────────────────────────────────────────────
const envs = ref<any[]>([])
const defaultPythonPath = ref<string | null>(null)
const envLastScan = ref<number | null>(null)
const envScanning = ref(false)
const showProbeDialog = ref(false)
const probePath = ref('')
const probeLoading = ref(false)

function agentHeaders() {
  return { Authorization: `Bearer ${agentStore.sessionToken}` }
}

async function fetchEnvs() {
  if (!agentStore.paired) return
  try {
    const res = await axios.get(`${agentStore.agentUrl}/api/v1/local/python-envs`, { headers: agentHeaders() })
    envs.value = res.data.envs || []
    defaultPythonPath.value = res.data.default_python_path
    envLastScan.value = res.data.last_scan
    envScanning.value = res.data.scanning ?? false
  } catch (err: any) {
    if (err?.response?.status === 401) agentStore.unpair()
  }
}

async function detectEnvs() {
  if (!agentStore.paired) return
  envScanning.value = true
  try {
    await axios.post(`${agentStore.agentUrl}/api/v1/local/python-envs/detect`, {}, { headers: agentHeaders() })
    ElMessage.info('环境扫描已启动，约需 15–30 秒，完成后自动刷新')
    // Poll every 3s until scanning flag clears
    const timer = setInterval(async () => {
      await fetchEnvs()
      if (!envScanning.value) clearInterval(timer)
    }, 3000)
    setTimeout(() => clearInterval(timer), 60000)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '启动扫描失败')
    envScanning.value = false
  }
}

async function probeEnv() {
  if (!probePath.value.trim()) { ElMessage.warning('请输入 Python 路径'); return }
  probeLoading.value = true
  try {
    const res = await axios.post(
      `${agentStore.agentUrl}/api/v1/local/python-envs/probe`,
      { python_path: probePath.value.trim() },
      { headers: agentHeaders() },
    )
    ElMessage.success(`探测成功：Python ${res.data.python_version}`)
    showProbeDialog.value = false
    probePath.value = ''
    await fetchEnvs()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '探测失败，请确认路径正确')
  } finally {
    probeLoading.value = false
  }
}

async function setDefault(pythonPath: string) {
  try {
    await axios.put(`${agentStore.agentUrl}/api/v1/local/python-envs/default`, { python_path: pythonPath }, { headers: agentHeaders() })
    defaultPythonPath.value = pythonPath
    ElMessage.success('默认外部环境已设置')
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '设置失败')
  }
}

async function removeEnv(envId: string) {
  try {
    await axios.delete(`${agentStore.agentUrl}/api/v1/local/python-envs/${envId}`, { headers: agentHeaders() })
    await fetchEnvs()
    ElMessage.success('已移除')
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '移除失败')
  }
}

function envSourceType(source: string) {
  const m: Record<string, string> = { conda: 'primary', pyenv: 'warning', system: 'info', custom: 'success' }
  return m[source] ?? 'info'
}

function fmtTime(ts: number) {
  return new Date(ts * 1000).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  if (agentStore.paired && agentStore.isOnline && !agentStore.envInfo) {
    agentStore.fetchAgentEnv()
  }
  fetchEnvs()
})
</script>

<style scoped>
.settings-page { display: flex; flex-direction: column; gap: 24px; max-width: 760px; }
.glass-card {
  background: rgba(22, 28, 36, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}
.section-title { margin: 0 0 16px; font-size: 1.1rem; font-weight: 700; color: #cbd5e1; }
.info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.info-grid.mt { margin-top: 14px; }
.info-item { display: flex; flex-direction: column; gap: 4px; }
.lbl { font-size: 0.78rem; color: #64748b; text-transform: uppercase; }
.val { font-size: 0.98rem; color: #e6edf3; font-weight: 600; }
.val.mono { font-family: ui-monospace, monospace; font-size: 0.82rem; }
.gradient-btn { background: linear-gradient(135deg, #6366f1, #a855f7) !important; border: none !important; color: #fff !important; font-weight: 600; }
.status-line { display: flex; align-items: center; gap: 12px; font-size: 0.95rem; }
.dot { width: 10px; height: 10px; border-radius: 50%; }
.dot.on { background: #3fb950; box-shadow: 0 0 10px #3fb950; }
.dot.off { background: #f85149; }
.about { font-size: 1rem; color: #e6edf3; margin: 0; }
.about-sub { font-size: 0.85rem; color: #64748b; margin: 6px 0 0; }

/* Python 环境管理 */
.helper { font-size: 0.85rem; color: #64748b; margin: 0 0 16px; line-height: 1.5; }
.env-toolbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
.env-meta { font-size: 0.78rem; color: #64748b; }
.env-meta.scanning { color: #f59e0b; }
.env-empty { text-align: center; padding: 24px 0; color: #64748b; font-size: 0.9rem; }
.env-list { display: flex; flex-direction: column; gap: 12px; }
.env-card {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  padding: 14px 16px;
  transition: border-color .2s;
}
.env-card.env-default { border-color: rgba(16,185,129,0.4); }
.env-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.env-name { font-weight: 600; color: #cbd5e1; font-size: 0.95rem; flex: 1; }
.env-path { font-family: monospace; font-size: 0.78rem; color: #64748b; margin-bottom: 8px; word-break: break-all; }
.env-caps { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.cap-badge { font-size: 0.72rem; padding: 2px 8px; border-radius: 99px; font-weight: 600; }
.cap-ok { background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.3); }
.cap-miss { background: rgba(100,116,139,0.1); color: #475569; border: 1px solid rgba(100,116,139,0.2); }
.env-actions { display: flex; gap: 8px; }
</style>
