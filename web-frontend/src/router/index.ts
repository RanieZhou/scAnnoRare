import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../pages/Dashboard.vue')
  },
  {
    path: '/agent',
    name: 'AgentPair',
    component: () => import('../pages/AgentPair.vue')
  },
  {
    path: '/datasets',
    name: 'Datasets',
    component: () => import('../pages/Datasets.vue')
  },
  {
    path: '/experiments',
    name: 'Experiments',
    component: () => import('../pages/Experiments.vue')
  },
  {
    path: '/evaluation',
    name: 'Evaluation',
    component: () => import('../pages/Evaluation.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
