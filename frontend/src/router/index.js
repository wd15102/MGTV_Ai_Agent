import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '大屏监控' }
  },
  {
    path: '/cases',
    name: 'Cases',
    component: () => import('@/views/Cases.vue'),
    meta: { title: '用例管理' }
  },
  {
    path: '/devices',
    name: 'Devices',
    component: () => import('@/views/Devices.vue'),
    meta: { title: '设备监控' }
  },
  {
    path: '/executions',
    name: 'Executions',
    component: () => import('@/views/Executions.vue'),
    meta: { title: '执行控制' }
  },
  {
    path: '/reports',
    name: 'Reports',
    component: () => import('@/views/Reports.vue'),
    meta: { title: '测试报告' }
  },
  {
    path: '/ai',
    name: 'AI',
    component: () => import('@/views/AIStatus.vue'),
    meta: { title: 'AI 状态' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title} - AI 智能测试平台`
  next()
})

export default router
