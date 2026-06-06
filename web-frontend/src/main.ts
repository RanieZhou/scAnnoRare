import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'
import axios from 'axios'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'  // Curated sleek dark mode
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

// ── 全局 axios 鉴权拦截器 ─────────────────────────────────────────────────────
// 仅给 Web 后端(8000)请求附加 JWT；Agent(17890)请求保持自身 session_token 鉴权。
const isWebApi = (url = '') => url.includes(':8000') || url.startsWith('/api/v1')

axios.interceptors.request.use((config) => {
  if (isWebApi(config.url)) {
    const token = localStorage.getItem('scannorare_auth_token')
    if (token) {
      config.headers = config.headers || {}
      ;(config.headers as any).Authorization = `Bearer ${token}`
    }
  }
  return config
})

axios.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && isWebApi(err.config?.url)) {
      localStorage.removeItem('scannorare_auth_token')
      localStorage.removeItem('scannorare_username')
      localStorage.removeItem('scannorare_user_id')
      if (router.currentRoute.value.path !== '/login') {
        router.push('/login')
      }
    }
    return Promise.reject(err)
  },
)

const app = createApp(App)
const pinia = createPinia()

// Register all element icons
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(pinia)
app.use(router)
app.use(ElementPlus)
app.mount('#app')
