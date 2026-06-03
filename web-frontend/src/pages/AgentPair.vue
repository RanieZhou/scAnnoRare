<template>
  <div class="agent-pair-page">
    <div class="pair-status-banner glass-card">
      <div class="status-circle" :class="{ 'pulse-green': agentStore.isOnline, 'pulse-red': !agentStore.isOnline }"></div>
      <div class="status-detail">
        <h3>Local Agent 连接诊断</h3>
        <p v-if="agentStore.isOnline">
          系统检测到本地运行中的代理服务，端口：17890，当前状态：<span class="status-text green">{{ agentStore.paired ? '已授权配对' : '等待配对验证' }}</span>
        </p>
        <p v-else class="status-text red">
          未检测到本地 Agent 服务。请在终端执行 `python local-agent/main.py` 开启本地生信服务，并确保监听于 127.0.0.1:17890
        </p>
      </div>
    </div>

    <div class="main-layout">
      <!-- Left side: Pairing Input -->
      <div class="left-col glass-card">
        <h3 class="section-title">🔑 节点配对授权</h3>
        
        <div v-if="!agentStore.paired" class="pair-form">
          <p class="form-desc">
            请输入本地桌面客户端或终端生成的配对码。配对码有效期为 5 分钟，单次验证成功后返回 session_token 进行会话保活。
          </p>
          
          <el-form :model="form" label-position="top">
            <el-form-item label="本地配对码 (Pairing Code)" required>
              <el-input 
                v-model="form.pairingCode" 
                placeholder="请输入 6-8 位大写字母或数字" 
                size="large"
                class="neon-input"
                :maxlength="8"
              />
            </el-form-item>
            
            <el-button 
              type="primary" 
              size="large" 
              class="gradient-btn w-100" 
              :loading="pairingLoading" 
              :disabled="!agentStore.isOnline"
              @click="handlePair"
            >
              发起节点配对
            </el-button>
          </el-form>
          
          <!-- Quick Dev Option (Auto-generate local code) -->
          <div class="dev-quick-pair" v-if="agentStore.isOnline">
            <el-divider>开发者快速测试</el-divider>
            <el-button size="small" type="info" plain class="w-100" @click="autoGenerateAndPair">
              一键在本地生成配对码并授权
            </el-button>
          </div>
        </div>

        <div v-else class="paired-details">
          <div class="token-panel">
            <span class="meta-label">已授权 Session Token</span>
            <code class="token-value">{{ agentStore.sessionToken.substring(0, 16) }}...</code>
          </div>
          
          <el-button type="danger" size="large" plain class="w-100" @click="handleUnpair">
            解除节点配对授权
          </el-button>
        </div>
      </div>

      <!-- Right side: Resource Diagnostics -->
      <div class="right-col glass-card" v-if="agentStore.paired && agentStore.envInfo">
        <h3 class="section-title">🖥️ 本地算力与依赖环境诊断</h3>
        
        <!-- Server metadata -->
        <div class="spec-grid">
          <div class="spec-item">
            <span class="meta-label">操作系统</span>
            <span class="meta-value">{{ agentStore.envInfo.os }}</span>
          </div>
          <div class="spec-item">
            <span class="meta-label">Python 引擎</span>
            <span class="meta-value">v{{ agentStore.envInfo.python_version }}</span>
          </div>
        </div>

        <el-divider />

        <!-- Resources progress bars -->
        <h4 class="sub-section-title">📊 硬件算力消耗</h4>
        <div class="resource-meters">
          <div class="meter-item">
            <div class="meter-header">
              <span>CPU 逻辑核心数</span>
              <span class="meter-val">{{ agentStore.envInfo.cpu_count }} 核</span>
            </div>
          </div>

          <div class="meter-item">
            <div class="meter-header">
              <span>物理内存</span>
              <span class="meter-val">{{ agentStore.envInfo.memory_available_gb }}GB 可用 / {{ agentStore.envInfo.memory_total_gb }}GB 总量</span>
            </div>
            <el-progress 
              :percentage="Math.round(((agentStore.envInfo.memory_total_gb - agentStore.envInfo.memory_available_gb) / agentStore.envInfo.memory_total_gb) * 100)" 
              :stroke-width="12"
              color="#6366f1"
            />
          </div>

          <!-- GPU details if available -->
          <div class="meter-item" v-if="agentStore.envInfo.gpu_available">
            <div class="meter-header">
              <span>NVIDIA GPU 显卡 (CUDA 可用)</span>
              <span class="meter-val">{{ agentStore.envInfo.gpu_devices[0]?.name }}</span>
            </div>
            <div class="gpu-memory">
              <span>显存占用: {{ agentStore.envInfo.gpu_devices[0]?.memory_used_gb }}GB / {{ agentStore.envInfo.gpu_devices[0]?.memory_total_gb }}GB</span>
              <el-progress 
                :percentage="Math.round((agentStore.envInfo.gpu_devices[0]?.memory_used_gb / agentStore.envInfo.gpu_devices[0]?.memory_total_gb) * 100)" 
                :stroke-width="12"
                color="#a855f7"
              />
            </div>
          </div>
          <div class="meter-item no-gpu" v-else>
            <div class="meter-header">
              <span>GPU 加速</span>
              <span class="meter-val text-muted">未检测到 NVIDIA GPU 设备，将降级使用 CPU 计算</span>
            </div>
          </div>
        </div>

        <el-divider />

        <!-- Omics package table -->
        <h4 class="sub-section-title">🧪 关键单细胞生信包依赖</h4>
        <el-table :data="packageData" style="width: 100%" size="small" class="dark-table">
          <el-table-column prop="name" label="依赖库" />
          <el-table-column prop="version" label="检测版本">
            <template #default="scope">
              <el-tag :type="scope.row.version === 'missing' ? 'danger' : 'success'" size="small">
                {{ scope.row.version === 'missing' ? '未安装' : 'v' + scope.row.version }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
      
      <!-- Placeholder when not paired -->
      <div class="right-col glass-card empty-state" v-else>
        <el-empty description="授权配对本地节点后，将实时调取并渲染硬件指标与单细胞生信依赖分析" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useAgentStore } from '../stores/agent'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const agentStore = useAgentStore()
const pairingLoading = ref(false)

const form = reactive({
  pairingCode: ''
})

// Package dictionary parsing
const packageData = computed(() => {
  if (!agentStore.envInfo || !agentStore.envInfo.packages) return []
  return Object.entries(agentStore.envInfo.packages).map(([name, ver]) => ({
    name,
    version: ver
  }))
})

// Normal pairing flow
const handlePair = async () => {
  if (!form.pairingCode) {
    ElMessage.warning('请输入配对码')
    return
  }
  
  pairingLoading.value = true
  try {
    const res = await axios.post(`${agentStore.agentUrl}/api/v1/local/pair`, {
      pairing_code: form.pairingCode.toUpperCase(),
      origin: agentStore.webOrigin
    })
    
    if (res.data.success) {
      agentStore.setPairing(res.data.session_token)
      ElMessage.success('本地节点成功连接并授权！')
      await agentStore.fetchAgentEnv()
    }
  } catch (err: any) {
    const msg = err.response?.data?.detail || '配对失败，请检查配对码是否正确或过期'
    ElMessage.error(msg)
  } finally {
    pairingLoading.value = false
  }
}

// Dev rapid pairing (calls node helper to generate local code, then auto pairs it!)
const autoGenerateAndPair = async () => {
  try {
    // 1. Generate code on agent
    const resGen = await axios.post(`${agentStore.agentUrl}/api/v1/local/admin/generate-pairing-code`)
    const code = resGen.data.pairing_code
    form.pairingCode = code
    
    // 2. Perform normal pair
    await handlePair()
  } catch (err) {
    ElMessage.error('无法自动获取配对码')
  }
}

const handleUnpair = async () => {
  try {
    await axios.post(`${agentStore.agentUrl}/api/v1/local/unpair`, {}, {
      headers: {
        'Authorization': `Bearer ${agentStore.sessionToken}`
      }
    })
  } catch (e) {}
  agentStore.unpair()
  form.pairingCode = ''
  ElMessage.info('已断开与本地节点的授权连接')
}
</script>

<style scoped>
.agent-pair-page {
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

.pair-status-banner {
  display: flex;
  align-items: center;
  gap: 20px;
}

.status-circle {
  width: 14px;
  height: 14px;
  border-radius: 50%;
}

.pulse-green {
  background-color: #10b981;
  box-shadow: 0 0 12px #10b981;
  animation: pulse 2s infinite;
}

.pulse-red {
  background-color: #ef4444;
  box-shadow: 0 0 12px #ef4444;
}

@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.status-detail h3 {
  margin: 0 0 6px 0;
  font-size: 1.1rem;
}

.status-detail p {
  margin: 0;
  color: #94a3b8;
  font-size: 0.9rem;
}

.status-text.green { color: #10b981; font-weight: 600; }
.status-text.red { color: #ef4444; font-weight: 600; }

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

.form-desc {
  font-size: 0.85rem;
  color: #64748b;
  line-height: 1.5;
  margin-bottom: 20px;
}

.neon-input :deep(.el-input__wrapper) {
  background-color: rgba(255, 255, 255, 0.02) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  box-shadow: none !important;
  transition: all 0.3s ease;
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
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
}

.gradient-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.3);
}

.token-panel {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 24px;
}

.token-value {
  font-family: monospace;
  font-size: 1.05rem;
  color: #cbd5e1;
  word-break: break-all;
}

/* Resource styling */
.spec-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.spec-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-size: 0.8rem;
  color: #64748b;
  text-transform: uppercase;
}

.meta-value {
  font-size: 1.05rem;
  font-weight: 600;
  color: #cbd5e1;
}

.sub-section-title {
  margin-top: 0;
  margin-bottom: 16px;
  font-size: 0.95rem;
  color: #94a3b8;
}

.resource-meters {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.meter-header {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  margin-bottom: 6px;
  color: #cbd5e1;
}

.meter-val {
  font-weight: 600;
}

.gpu-memory {
  margin-top: 8px;
  font-size: 0.85rem;
  color: #94a3b8;
}

.no-gpu {
  background: rgba(255, 255, 255, 0.01);
  border: 1px dashed rgba(255, 255, 255, 0.06);
  padding: 12px 16px;
  border-radius: 8px;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

:deep(.el-table) {
  background-color: transparent !important;
}
:deep(.el-table th), :deep(.el-table tr) {
  background-color: transparent !important;
  color: #cbd5e1 !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04) !important;
}
</style>
