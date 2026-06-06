import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../pages/Login.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../pages/Dashboard.vue'),
  },
  {
    path: '/agent',
    name: 'AgentPair',
    component: () => import('../pages/AgentPair.vue'),
  },
  {
    path: '/datasets',
    name: 'Datasets',
    component: () => import('../pages/Datasets.vue'),
  },
  {
    path: '/experiments',
    name: 'Experiments',
    component: () => import('../pages/Experiments.vue'),
  },
  {
    path: '/evaluation',
    name: 'Evaluation',
    component: () => import('../pages/Evaluation.vue'),
  },
  {
    path: '/reports',
    name: 'Reports',
    component: () => import('../pages/Reports.vue'),
  },
  {
    path: '/projects',
    name: 'Projects',
    component: () => import('../pages/Projects.vue'),
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../pages/Settings.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Route guard: redirect to /login if not authenticated
router.beforeEach((to) => {
  const authStore = useAuthStore()
  if (!to.meta.public && !authStore.loggedIn) {
    return '/login'
  }
  // Already logged in, don't show login page again
  if (to.path === '/login' && authStore.loggedIn) {
    return '/'
  }
})

export default router
