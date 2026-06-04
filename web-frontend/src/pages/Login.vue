<template>
  <div class="login-root">
    <!-- Background decoration -->
    <div class="bg-orb orb-1"></div>
    <div class="bg-orb orb-2"></div>

    <div class="login-card glass-card">
      <!-- Logo -->
      <div class="brand-area">
        <div class="brand-logo">🔮</div>
        <h1 class="brand-name">scAnnoRare</h1>
        <p class="brand-sub">单细胞细胞类型注释与稀有细胞识别多方法评估系统 V1.0</p>
      </div>

      <!-- Tab switcher -->
      <el-tabs v-model="activeTab" class="login-tabs" stretch>
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" label-position="top" class="auth-form" @submit.prevent="handleLogin">
            <el-form-item label="用户名">
              <el-input
                v-model="loginForm.username"
                placeholder="admin"
                prefix-icon="User"
                class="neon-input"
                size="large"
              />
            </el-form-item>
            <el-form-item label="密码">
              <el-input
                v-model="loginForm.password"
                type="password"
                placeholder="密码"
                prefix-icon="Lock"
                class="neon-input"
                size="large"
                show-password
                @keyup.enter="handleLogin"
              />
            </el-form-item>
            <el-button
              type="primary"
              class="submit-btn gradient-btn"
              size="large"
              :loading="loading"
              @click="handleLogin"
            >
              登录系统
            </el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="注册" name="register">
          <el-form :model="registerForm" label-position="top" class="auth-form">
            <el-form-item label="邮箱">
              <el-input
                v-model="registerForm.email"
                placeholder="user@example.com"
                prefix-icon="Message"
                class="neon-input"
                size="large"
              />
            </el-form-item>
            <el-form-item label="用户名">
              <el-input
                v-model="registerForm.username"
                placeholder="自定义用户名"
                prefix-icon="User"
                class="neon-input"
                size="large"
              />
            </el-form-item>
            <el-form-item label="密码">
              <el-input
                v-model="registerForm.password"
                type="password"
                placeholder="设置密码"
                prefix-icon="Lock"
                class="neon-input"
                size="large"
                show-password
              />
            </el-form-item>
            <el-button
              type="primary"
              class="submit-btn gradient-btn"
              size="large"
              :loading="loading"
              @click="handleRegister"
            >
              创建账号
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <!-- Quick dev login hint -->
      <div class="dev-hint">
        <span>首次使用默认账号：</span>
        <code @click="quickFill">admin / admin</code>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router    = useRouter()
const authStore = useAuthStore()

const activeTab = ref('login')
const loading   = ref(false)

const loginForm    = reactive({ username: '', password: '' })
const registerForm = reactive({ email: '', username: '', password: '' })

function quickFill() {
  loginForm.username = 'admin'
  loginForm.password = 'admin'
  activeTab.value    = 'login'
}

async function handleLogin() {
  if (!loginForm.username || !loginForm.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await authStore.login(loginForm.username, loginForm.password)
    ElMessage.success(`欢迎回来，${authStore.username}！`)
    router.push('/')
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail ?? '登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!registerForm.email || !registerForm.username || !registerForm.password) {
    ElMessage.warning('请填写所有注册信息')
    return
  }
  loading.value = true
  try {
    await authStore.register(registerForm.email, registerForm.username, registerForm.password)
    ElMessage.success('注册成功，请登录')
    activeTab.value         = 'login'
    loginForm.username      = registerForm.username
    loginForm.password      = registerForm.password
    registerForm.email      = ''
    registerForm.username   = ''
    registerForm.password   = ''
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail ?? '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-root {
  min-height: 100vh;
  width: 100vw;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #080a0e;
  position: relative;
  overflow: hidden;
}

.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.35;
  pointer-events: none;
}
.orb-1 { width: 500px; height: 500px; background: #6366f1; top: -150px; left: -150px; }
.orb-2 { width: 400px; height: 400px; background: #a855f7; bottom: -100px; right: -100px; }

.glass-card {
  position: relative;
  z-index: 1;
  background: rgba(18, 22, 30, 0.75);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 24px;
  padding: 48px 40px 36px;
  width: 420px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.5);
}

.brand-area {
  text-align: center;
  margin-bottom: 32px;
}
.brand-logo {
  font-size: 3rem;
  margin-bottom: 10px;
}
.brand-name {
  font-size: 2rem;
  font-weight: 800;
  margin: 0;
  background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.04em;
}
.brand-sub {
  margin: 8px 0 0;
  font-size: 0.78rem;
  color: #64748b;
  line-height: 1.4;
}

.login-tabs :deep(.el-tabs__nav-wrap::after) {
  background-color: rgba(255, 255, 255, 0.06);
}
.login-tabs :deep(.el-tabs__item) {
  color: #64748b;
  font-size: 1rem;
  font-weight: 600;
}
.login-tabs :deep(.el-tabs__item.is-active) { color: #a855f7; }
.login-tabs :deep(.el-tabs__active-bar)      { background-color: #a855f7; }

.auth-form { padding-top: 8px; }

.neon-input :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.03) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  box-shadow: none !important;
  transition: all 0.3s;
}
.neon-input :deep(.el-input__wrapper):hover,
.neon-input :deep(.el-input__wrapper.is-focus) {
  border-color: #6366f1 !important;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
}
.neon-input :deep(.el-input__inner) { color: #f1f5f9 !important; }

.submit-btn {
  width: 100%;
  margin-top: 8px;
  height: 44px;
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.gradient-btn {
  background: linear-gradient(135deg, #6366f1, #a855f7) !important;
  border: none !important;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.35);
  transition: all 0.3s;
}
.gradient-btn:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(99, 102, 241, 0.45); }

.dev-hint {
  margin-top: 24px;
  text-align: center;
  font-size: 0.82rem;
  color: #475569;
}
.dev-hint code {
  margin-left: 6px;
  padding: 2px 8px;
  background: rgba(99, 102, 241, 0.12);
  color: #818cf8;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}
.dev-hint code:hover { background: rgba(99, 102, 241, 0.22); }
</style>
