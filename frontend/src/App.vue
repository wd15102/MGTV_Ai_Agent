<template>
  <div id="app" class="min-h-screen bg-[#f0f2f5]">
    <!-- 左侧导航栏 (PerfDog 风格) -->
    <aside class="fixed left-0 top-0 bottom-0 w-[200px] bg-[#1a1b2e] z-50 flex flex-col">
      <!-- Logo 区域 -->
      <div class="h-16 flex items-center px-5 border-b border-[rgba(255,255,255,0.06)] flex-shrink-0">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-[#1677ff] to-[#4096ff] flex items-center justify-center text-white font-bold text-sm shadow-lg shadow-[rgba(22,119,255,0.3)]">
            N
          </div>
          <div>
            <h1 class="text-base font-bold text-white tracking-wider leading-tight">NEXUS</h1>
            <p class="text-[9px] text-[rgba(255,255,255,0.35)] tracking-[0.15em] uppercase leading-tight">AI TEST PLATFORM</p>
          </div>
        </div>
      </div>

      <!-- 导航项 -->
      <nav class="flex-1 py-3 overflow-y-auto">
        <router-link
          v-for="link in navLinks"
          :key="link.path"
          :to="link.path"
          class="nav-item"
          :class="{ 'nav-item-active': isActive(link.path) }"
        >
          <span class="nav-indicator"></span>
          <!-- SVG 图标 -->
          <span class="nav-icon" v-html="link.iconSvg"></span>
          <span class="nav-label">{{ link.label }}</span>
        </router-link>
      </nav>

      <!-- 底部版本信息 -->
      <div class="px-5 py-3 border-t border-[rgba(255,255,255,0.06)] flex-shrink-0">
        <p class="text-[10px] text-[rgba(255,255,255,0.25)] font-mono">v2.0.0</p>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="ml-[200px] min-h-screen flex flex-col">
      <!-- 顶栏 (PerfDog 风格) -->
      <header class="sticky top-0 z-40 bg-white border-b border-gray-100 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
        <div class="flex items-center justify-between h-14 px-6">
          <!-- 页面标题 -->
          <div>
            <h2 class="text-base font-semibold text-[#1f1f1f]">{{ currentPageTitle }}</h2>
          </div>

          <!-- 右侧操作区 -->
          <div class="flex items-center gap-4">
            <span class="text-sm font-mono text-[#999] tracking-wider">{{ currentTime }}</span>
            <div class="flex items-center gap-1.5">
              <span class="status-dot status-dot-online"></span>
              <span class="text-xs text-[#999]">系统运行中</span>
            </div>
          </div>
        </div>
      </header>

      <!-- 页面内容 -->
      <main class="flex-1 p-6">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const currentTime = ref('')
let timeInterval = null

const navLinks = [
  {
    path: '/',
    label: '监控大屏',
    iconSvg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>'
  },
  {
    path: '/devices',
    label: '设备监控',
    iconSvg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>'
  },
  {
    path: '/cases',
    label: '用例管理',
    iconSvg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>'
  },
  {
    path: '/executions',
    label: '执行控制',
    iconSvg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>'
  },
  {
    path: '/reports',
    label: '测试报告',
    iconSvg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M16 13H8M16 17H8M10 9H8"/></svg>'
  },
  {
    path: '/ai',
    label: 'AI 状态',
    iconSvg: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1.27A7.04 7.04 0 0 1 17 21h-4a3 3 0 0 1-3-3v-1"/><path d="M6.5 13.5c-1.5 0-2.5-1-2.5-2.5S5 8.5 6.5 8.5 9 9.5 9 11s-1 2.5-2.5 2.5z"/><path d="M4 2v4M2 4h4"/><path d="M16 6a2 2 0 1 0 0-4 2 2 0 0 0 0 4z"/></svg>'
  },
]

const pageTitles = {
  '/': '监控大屏',
  '/devices': '设备监控',
  '/cases': '用例管理',
  '/executions': '执行控制',
  '/reports': '测试报告',
  '/ai': 'AI 状态',
}

const currentPageTitle = computed(() => {
  return pageTitles[route.path] || 'NEXUS'
})

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

function updateTime() {
  const now = new Date()
  const h = String(now.getHours()).padStart(2, '0')
  const m = String(now.getMinutes()).padStart(2, '0')
  const s = String(now.getSeconds()).padStart(2, '0')
  currentTime.value = `${h}:${m}:${s}`
}

onMounted(() => {
  updateTime()
  timeInterval = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  if (timeInterval) clearInterval(timeInterval)
})
</script>

<style>
/* 导航项样式 - PerfDog 风格 */
.nav-item {
  @apply flex items-center gap-3 px-5 py-2.5 text-sm transition-all duration-150 cursor-pointer relative;
  color: rgba(255, 255, 255, 0.55);
  text-decoration: none;
  margin: 1px 8px;
  border-radius: 6px;
}
.nav-item:hover {
  color: rgba(255, 255, 255, 0.85);
  background: rgba(255, 255, 255, 0.06);
}
.nav-item-active {
  color: #ffffff !important;
  background: rgba(22, 119, 255, 0.15) !important;
}

/* 左侧蓝色竖条指示器 */
.nav-indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 0;
  background: #1677ff;
  border-radius: 0 2px 2px 0;
  transition: height 0.2s ease;
}
.nav-item-active .nav-indicator {
  height: 18px;
}

/* 图标容器 */
.nav-icon {
  @apply flex-shrink-0 flex items-center justify-center;
  width: 20px;
  height: 20px;
}

/* SVG 图标颜色 */
.nav-item-active .nav-icon {
  color: #1677ff;
}

/* 文字 */
.nav-label {
  @apply font-medium;
}

/* 页面过渡 */
.page-enter-active,
.page-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.page-enter {
  opacity: 0;
  transform: translateY(8px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
