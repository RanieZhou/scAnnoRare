<template>
  <el-config-provider :locale="zhCn">
    <!-- Login view: full-screen, no shell -->
    <router-view v-if="isLoginRoute" />

    <!-- Main shell -->
    <div v-else class="app-layout">
      <!-- Sidebar -->
      <aside class="sidebar glass-effect">
        <div class="brand">
          <div class="brand-logo">🔮</div>
          <div class="brand-name">scAnnoRare</div>
          <span class="version-tag">V1.0</span>
        </div>

        <nav class="nav-menu">
          <router-link to="/" class="nav-item">
            <el-icon><Odometer /></el-icon>
            <span>首页控制台</span>
          </router-link>

          <router-link to="/agent" class="nav-item">
            <el-icon><Cpu /></el-icon>
            <span>计算节点配对</span>
            <span class="badge" :class="agentStore.isOnline ? 'dot-online' : 'dot-offline'"></span>
          </router-link>

          <router-link to="/datasets" class="nav-item">
            <el-icon><FolderOpened /></el-icon>
            <span>数据集注册</span>
          </router-link>

          <router-link to="/experiments" class="nav-item">
            <el-icon><ScaleToOriginal /></el-icon>
            <span>实验配置管理</span>
          </router-link>

          <router-link to="/evaluation" class="nav-item">
            <el-icon><DataAnalysis /></el-icon>
            <span>评估与对比</span>
          </router-link>

          <router-link to="/reports" class="nav-item">
            <el-icon><Document /></el-icon>
            <span>报告中心</span>
          </router-link>
        </nav>

        <!-- Bottom user info -->
        <div class="sidebar-footer">
          <div class="user-row">
            <el-icon><User /></el-icon>
            <span class="username-text">{{ authStore.username || 'admin' }}</span>
          </div>
          <el-button size="small" type="danger" plain class="logout-btn" @click="handleLogout">
            退出
          </el-button>
        </div>
      </aside>

      <!-- Main Container -->
      <div class="main-container">
        <!-- Topbar -->
        <header class="topbar glass-effect">
          <div class="header-left">
            <el-breadcrumb separator="/">
              <el-breadcrumb-item>scAnnoRare</el-breadcrumb-item>
              <el-breadcrumb-item>{{ $route.name }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>

          <div class="header-right">
            <el-tag
              :type="agentStore.isOnline ? 'success' : 'danger'"
              class="agent-badge"
              effect="dark"
            >
              <el-icon class="el-icon--left">
                <CircleCheck v-if="agentStore.isOnline" />
                <Warning v-else />
              </el-icon>
              Local Agent: {{ agentStore.isOnline ? '已连接 (127.0.0.1)' : '未连接' }}
            </el-tag>
          </div>
        </header>

        <!-- Page Content -->
        <main class="content-view">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </main>
      </div>
    </div>
  </el-config-provider>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAgentStore } from './stores/agent'
import { useAuthStore }  from './stores/auth'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import {
  Odometer, Cpu, FolderOpened, ScaleToOriginal,
  DataAnalysis, Document, User, CircleCheck, Warning,
} from '@element-plus/icons-vue'

const route      = useRoute()
const router     = useRouter()
const agentStore = useAgentStore()
const authStore  = useAuthStore()

const isLoginRoute = computed(() => route.path === '/login')

let healthTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  await agentStore.checkAgentHealth()
  if (agentStore.isOnline && agentStore.paired) {
    await agentStore.fetchAgentEnv()
  }
  healthTimer = setInterval(() => agentStore.checkAgentHealth(), 5000)
})

onUnmounted(() => {
  if (healthTimer) clearInterval(healthTimer)
})

function handleLogout() {
  authStore.logout()
  agentStore.unpair()
  ElMessage.info('已退出登录')
  router.push('/login')
}
</script>

<style>
:root {
  --bg-color: #080a0e;
  --panel-bg: rgba(13, 17, 24, 0.7);
  --border-color: rgba(255, 255, 255, 0.06);
  --text-main: #f1f5f9;
  --text-muted: #64748b;
  --primary-color: #6366f1;
  --primary-gradient: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
  --sidebar-width: 250px;
}

body {
  margin: 0; padding: 0;
  background-color: var(--bg-color);
  color: var(--text-main);
  font-family: 'Outfit', 'Segoe UI', system-ui, -apple-system, sans-serif;
  overflow: hidden;
}

.app-layout {
  display: flex; height: 100vh; width: 100vw;
  background:
    radial-gradient(circle at 10% 20%, rgba(99,102,241,0.08) 0%, transparent 40%),
    radial-gradient(circle at 90% 80%, rgba(168,85,247,0.06) 0%, transparent 45%);
}

.glass-effect {
  background: var(--panel-bg);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--border-color);
}

/* Sidebar */
.sidebar {
  width: var(--sidebar-width); height: 100%;
  display: flex; flex-direction: column;
  box-sizing: border-box; z-index: 100;
  border-top: none; border-bottom: none; border-left: none;
}

.brand {
  padding: 24px; display: flex; align-items: center; gap: 12px;
  border-bottom: 1px solid var(--border-color);
}
.brand-logo { font-size: 1.8rem; }
.brand-name {
  font-size: 1.4rem; font-weight: 800;
  background: var(--primary-gradient);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  letter-spacing: -0.04em;
}
.version-tag {
  font-size: 0.65rem; padding: 2px 6px; border-radius: 4px;
  background: rgba(99,102,241,0.15); color: #a855f7; font-weight: 700;
}

.nav-menu {
  padding: 20px 12px; display: flex; flex-direction: column;
  gap: 8px; flex-grow: 1;
}
.nav-item {
  display: flex; align-items: center; gap: 12px; padding: 12px 16px;
  color: #94a3b8; text-decoration: none; border-radius: 12px;
  font-weight: 500; font-size: 0.95rem; transition: all 0.3s;
}
.nav-item:hover { color: var(--text-main); background: rgba(255,255,255,0.03); }
.nav-item.router-link-active {
  color: #ffffff;
  background: var(--primary-gradient);
  box-shadow: 0 4px 20px rgba(99,102,241,0.25);
}

.badge { width: 6px; height: 6px; border-radius: 50%; margin-left: auto; }
.dot-online  { background-color: #10b981; box-shadow: 0 0 10px #10b981; }
.dot-offline { background-color: #ef4444; }

.sidebar-footer {
  padding: 16px; border-top: 1px solid var(--border-color);
  display: flex; align-items: center; justify-content: space-between;
}
.user-row { display: flex; align-items: center; gap: 8px; font-size: 0.9rem; color: #94a3b8; }
.username-text { max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.logout-btn { padding: 4px 10px !important; }

/* Main */
.main-container { flex-grow: 1; display: flex; flex-direction: column; overflow: hidden; }
.topbar {
  height: 64px; display: flex; align-items: center;
  justify-content: space-between; padding: 0 24px; box-sizing: border-box;
  border-top: none; border-left: none; border-right: none;
}
.header-right { display: flex; align-items: center; gap: 20px; }
.agent-badge  { border: 1px solid rgba(255,255,255,0.08) !important; }

.content-view { flex-grow: 1; padding: 24px; overflow-y: auto; box-sizing: border-box; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to       { opacity: 0; }

.el-breadcrumb__inner { color: #64748b !important; }
.el-breadcrumb__item:last-child .el-breadcrumb__inner { color: #cbd5e1 !important; font-weight: 600; }
</style>
