<template>
  <div class="space-y-6">
    <!-- 标题 -->
    <div class="flex justify-between items-center">
      <h2 class="text-3xl font-bold text-gray-900">📊 实时监控大屏</h2>
      <div class="flex space-x-2">
        <button @click="refreshData" class="btn-primary">🔄 刷新</button>
        <button @click="toggleAutoRefresh" class="btn-secondary">
          {{ autoRefresh ? '⏸️ 暂停' : '▶️ 自动' }}
        </button>
      </div>
    </div>

    <!-- 设备状态卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div v-for="device in devices" :key="device.device_id" 
           class="card hover:shadow-xl transition-shadow">
        <div class="flex justify-between items-start">
          <div>
            <h3 class="text-xl font-semibold text-gray-900">{{ device.name }}</h3>
            <p class="text-sm text-gray-500">{{ device.device_id }}</p>
          </div>
          <span :class="statusClass(device.status)" class="badge">
            {{ device.status }}
          </span>
        </div>
        
        <div class="mt-4 grid grid-cols-2 gap-4">
          <div class="stat-box">
            <p class="stat-label">类型</p>
            <p class="stat-value">{{ device.type }}</p>
          </div>
          <div class="stat-box">
            <p class="stat-label">Android</p>
            <p class="stat-value">{{ device.android_version }}</p>
          </div>
          <div class="stat-box">
            <p class="stat-label">分辨率</p>
            <p class="stat-value">{{ device.resolution }}</p>
          </div>
          <div class="stat-box">
            <p class="stat-label">最后心跳</p>
            <p class="stat-value text-sm">{{ formatTime(device.last_heartbeat) }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 性能图表 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="card">
        <h3 class="card-title">📈 CPU/内存 使用率</h3>
        <div ref="cpuMemChart" class="chart-container"></div>
      </div>
      
      <div class="card">
        <h3 class="card-title">🎯 FPS 曲线</h3>
        <div ref="fpsChart" class="chart-container"></div>
      </div>
    </div>

    <!-- AI 状态 -->
    <div class="card">
      <h3 class="card-title">🤖 AI Agent 状态</h3>
      <div v-if="aiStatus" class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="stat-box">
          <p class="stat-label">状态</p>
          <p :class="aiStatus.status === 'ready' ? 'text-green-600' : 'text-red-600'" 
             class="stat-value">
            {{ aiStatus.status }}
          </p>
        </div>
        <div class="stat-box">
          <p class="stat-label">Qwen-VL</p>
          <p :class="aiStatus.qwen_enabled ? 'text-green-600' : 'text-gray-400'" 
             class="stat-value">
            {{ aiStatus.qwen_enabled ? '✅ 启用' : '❌ 未启用' }}
          </p>
        </div>
        <div class="stat-box">
          <p class="stat-label">YOLO</p>
          <p :class="aiStatus.yolo_enabled ? 'text-green-600' : 'text-gray-400'" 
             class="stat-value">
            {{ aiStatus.yolo_enabled ? '✅ 启用' : '❌ 未启用' }}
          </p>
        </div>
        <div class="stat-box">
          <p class="stat-label">OCR</p>
          <p :class="aiStatus.ocr_enabled ? 'text-green-600' : 'text-gray-400'" 
             class="stat-value">
            {{ aiStatus.ocr_enabled ? '✅ 启用' : '❌ 未启用' }}
          </p>
        </div>
      </div>
    </div>

    <!-- 实时日志 -->
    <div class="card">
      <h3 class="card-title">📋 实时日志</h3>
      <div class="bg-gray-900 text-green-400 font-mono text-sm p-4 rounded-lg h-64 overflow-y-auto">
        <div v-for="(log, idx) in logs" :key="idx" class="mb-1">
          <span class="text-gray-500">{{ log.timestamp }}</span>
          <span :class="log.level === 'ERROR' ? 'text-red-400' : 'text-green-400'">
            {{ log.content }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'

const devices = ref([])
const aiStatus = ref(null)
const logs = ref([])
const autoRefresh = ref(true)
let refreshInterval = null

// 图表实例
let cpuMemChartInstance = null
let fpsChartInstance = null

onMounted(async () => {
  await fetchData()
  initCharts()
  
  if (autoRefresh.value) {
    refreshInterval = setInterval(fetchData, 2000)
  }
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  if (cpuMemChartInstance) {
    cpuMemChartInstance.dispose()
  }
  if (fpsChartInstance) {
    fpsChartInstance.dispose()
  }
})

async function fetchData() {
  try {
    // 获取设备状态
    const devicesRes = await axios.get('/api/v1/devices')
    devices.value = devicesRes.data.data
    
    // 获取 AI 状态
    const aiRes = await axios.get('/api/v1/ai/status')
    aiStatus.value = aiRes.data.data
    
    // 更新图表
    updateCharts()
  } catch (error) {
    console.error('获取数据失败:', error)
  }
}

function initCharts() {
  // CPU/内存图表
  const cpuMemEl = document.querySelector('[ref="cpuMemChart"]')
  if (cpuMemEl) {
    cpuMemChartInstance = echarts.init(cpuMemEl)
    cpuMemChartInstance.setOption({
      title: { text: 'CPU/内存监控' },
      tooltip: { trigger: 'axis' },
      legend: { data: ['CPU (%)', '内存 (%)'] },
      xAxis: { type: 'time' },
      yAxis: { type: 'value', max: 100 },
      series: [
        { name: 'CPU (%)', type: 'line', data: [] },
        { name: '内存 (%)', type: 'line', data: [] }
      ]
    })
  }
  
  // FPS 图表
  const fpsEl = document.querySelector('[ref="fpsChart"]')
  if (fpsEl) {
    fpsChartInstance = echarts.init(fpsEl)
    fpsChartInstance.setOption({
      title: { text: 'FPS 曲线' },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'time' },
      yAxis: { type: 'value' },
      series: [{ name: 'FPS', type: 'line', smooth: true, data: [] }]
    })
  }
}

function updateCharts() {
  // 这里应该从 WebSocket 获取实时数据
  // 暂时使用模拟数据
  const now = new Date()
  
  if (cpuMemChartInstance) {
    const option = cpuMemChartInstance.getOption()
    option.series[0].data.push([now, Math.random() * 100])
    option.series[1].data.push([now, Math.random() * 100])
    cpuMemChartInstance.setOption(option)
  }
  
  if (fpsChartInstance) {
    const option = fpsChartInstance.getOption()
    option.series[0].data.push([now, Math.random() * 60])
    fpsChartInstance.setOption(option)
  }
}

function refreshData() {
  fetchData()
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    refreshInterval = setInterval(fetchData, 2000)
  } else {
    clearInterval(refreshInterval)
  }
}

function formatTime(isoString) {
  if (!isoString) return '-'
  const date = new Date(isoString)
  return date.toLocaleTimeString('zh-CN')
}

function statusClass(status) {
  return {
    'badge-success': status === 'online',
    'badge-warning': status === 'busy',
    'badge-danger': status === 'offline'
  }
}
</script>

<style scoped>
.badge {
  @apply px-3 py-1 rounded-full text-sm font-medium;
}
.badge-success {
  @apply bg-green-100 text-green-800;
}
.badge-warning {
  @apply bg-yellow-100 text-yellow-800;
}
.badge-danger {
  @apply bg-red-100 text-red-800;
}
</style>
