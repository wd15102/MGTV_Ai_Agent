<template>
  <PageCard title="监控大屏" class="page-card-wrap">
    <!-- 顶部统计卡片 -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="stat-card stat-accent-blue">
        <div class="stat-card-body">
          <p class="stat-label">设备总数</p>
          <p class="stat-value" style="color: #1677ff">{{ stats.totalDevices }}</p>
          <div class="stat-trend up">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"/></svg>
            <span>ALL</span>
          </div>
        </div>
      </div>
      <div class="stat-card stat-accent-green">
        <div class="stat-card-body">
          <p class="stat-label">在线设备</p>
          <p class="stat-value" style="color: #52c41a">{{ stats.onlineDevices }}</p>
          <div class="stat-trend up">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"/></svg>
            <span>ONLINE</span>
          </div>
        </div>
      </div>
      <div class="stat-card stat-accent-orange">
        <div class="stat-card-body">
          <p class="stat-label">执行中</p>
          <p class="stat-value" style="color: #faad14">{{ stats.runningTasks }}</p>
          <div class="stat-trend up">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"/></svg>
            <span>RUNNING</span>
          </div>
        </div>
      </div>
      <div class="stat-card stat-accent-purple">
        <div class="stat-card-body">
          <p class="stat-label">成功率</p>
          <p class="stat-value" style="color: #722ed1">{{ stats.successRate }}%</p>
          <div class="stat-trend up">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"/></svg>
            <span>SUCCESS</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 操作栏 -->
    <div class="flex justify-end gap-2">
      <button @click="refreshData" class="btn-primary text-xs px-3 py-1.5">
        <svg class="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
        刷新数据
      </button>
      <button @click="toggleAutoRefresh" class="btn-secondary text-xs px-3 py-1.5">
        {{ autoRefresh ? '暂停刷新' : '自动刷新' }}
      </button>
    </div>

    <!-- 设备状态 - PerfDog 风格的设备列表 -->
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h3 class="card-title flex items-center gap-2 mb-0">
          <svg class="w-4 h-4 text-[#1677ff]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>
          设备状态
        </h3>
        <span class="text-xs text-[#999]">{{ devices.length }} 台设备</span>
      </div>
      <div class="space-y-2">
        <div v-for="device in devices" :key="device.device_id"
             class="flex items-center gap-4 p-3 rounded-lg bg-[#fafafa] border border-[#f0f0f0] hover:border-[#d6e4ff] transition-all duration-200">
          <!-- 状态灯 -->
          <div class="flex-shrink-0">
            <span v-if="device.status === 'online'" class="status-dot status-dot-online"></span>
            <span v-else-if="device.status === 'busy'" class="status-dot status-dot-busy"></span>
            <span v-else class="status-dot status-dot-offline"></span>
          </div>
          <!-- 设备信息 -->
          <div class="flex-1 min-w-0 flex items-center gap-6">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <h4 class="text-sm font-semibold text-[#1f1f1f] truncate">{{ device.name }}</h4>
                <span :class="'badge ' + statusBadgeClass(device.status)" class="text-[10px] px-1.5 py-0">
                  {{ statusLabel(device.status) }}
                </span>
              </div>
            </div>
            <span class="text-xs text-[#999] whitespace-nowrap hidden sm:inline">{{ device.type }}</span>
            <span class="text-xs text-[#999] whitespace-nowrap hidden md:inline">Android {{ device.android_version }}</span>
            <span class="text-xs text-[#999] whitespace-nowrap hidden lg:inline">{{ device.resolution }}</span>
            <span class="text-xs text-[#999] whitespace-nowrap font-mono hidden xl:inline">{{ formatTime(device.last_heartbeat) }}</span>
          </div>
          <!-- 截图预览按钮 -->
          <button @click="takeScreenshot(device.device_id)"
                  class="flex-shrink-0 text-xs px-2.5 py-1.5 rounded border border-[#d9d9d9] text-[#666] hover:border-[#1677ff] hover:text-[#1677ff] transition-all">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
          </button>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div class="card">
        <h3 class="card-title flex items-center gap-2">
          <svg class="w-4 h-4 text-[#1677ff]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
          CPU / 内存
        </h3>
        <div ref="cpuMemChartRef" class="chart-container"></div>
      </div>
      <div class="card">
        <h3 class="card-title flex items-center gap-2">
          <svg class="w-4 h-4 text-[#1677ff]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          FPS 曲线
        </h3>
        <div ref="fpsChartRef" class="chart-container"></div>
      </div>
    </div>

    <!-- AI Agent 状态 -->
    <div class="card">
      <h3 class="card-title flex items-center gap-2">
        <svg class="w-4 h-4 text-[#1677ff]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1.27A7.04 7.04 0 0 1 17 21h-4a3 3 0 0 1-3-3v-1"/><path d="M6.5 13.5c-1.5 0-2.5-1-2.5-2.5S5 8.5 6.5 8.5 9 9.5 9 11s-1 2.5-2.5 2.5z"/></svg>
        AI Agent 状态
      </h3>
      <div v-if="aiStatus" class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="flex flex-col items-center p-3 rounded-lg bg-[#fafafa] border border-[#f0f0f0]">
          <span class="text-lg font-bold font-mono" :class="aiStatus.status === 'ready' ? 'text-[#52c41a]' : 'text-[#ff4d4f]'">
            {{ aiStatus.status }}
          </span>
          <span class="text-xs text-[#999] mt-1">状态</span>
        </div>
        <div class="flex flex-col items-center p-3 rounded-lg bg-[#fafafa] border border-[#f0f0f0]">
          <span class="text-lg font-bold font-mono" :class="aiStatus.qwen_enabled ? 'text-[#1677ff]' : 'text-[#999]'">
            {{ aiStatus.qwen_enabled ? '启用' : '未启用' }}
          </span>
          <span class="text-xs text-[#999] mt-1">Qwen-VL</span>
        </div>
        <div class="flex flex-col items-center p-3 rounded-lg bg-[#fafafa] border border-[#f0f0f0]">
          <span class="text-lg font-bold font-mono" :class="aiStatus.yolo_enabled ? 'text-[#52c41a]' : 'text-[#999]'">
            {{ aiStatus.yolo_enabled ? '启用' : '未启用' }}
          </span>
          <span class="text-xs text-[#999] mt-1">YOLO</span>
        </div>
        <div class="flex flex-col items-center p-3 rounded-lg bg-[#fafafa] border border-[#f0f0f0]">
          <span class="text-lg font-bold font-mono" :class="aiStatus.ocr_enabled ? 'text-[#722ed1]' : 'text-[#999]'">
            {{ aiStatus.ocr_enabled ? '启用' : '未启用' }}
          </span>
          <span class="text-xs text-[#999] mt-1">OCR</span>
        </div>
      </div>
    </div>

    <!-- 日志区域 -->
    <div class="card">
      <div class="flex items-center justify-between mb-3">
        <h3 class="card-title flex items-center gap-2 mb-0">
          <svg class="w-4 h-4 text-[#1677ff]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          实时日志
        </h3>
        <span class="text-xs text-[#999]">{{ logs.length }} 条</span>
      </div>
      <div class="bg-[#1a1b2e] rounded-lg h-56 overflow-y-auto p-4 font-mono text-sm">
        <div v-if="logs.length === 0" class="text-[rgba(255,255,255,0.3)] text-center py-8">
          <span class="animate-pulse">等待日志...</span>
        </div>
        <div v-for="(log, idx) in logs" :key="idx" class="mb-1.5 leading-relaxed">
          <span class="text-[rgba(255,255,255,0.3)] text-xs">[{{ log.timestamp }}]</span>
          <span :class="log.level === 'ERROR' ? 'text-[#ff4d4f]' : log.level === 'WARN' ? 'text-[#faad14]' : 'text-[#52c41a]'" class="text-xs">
            {{ log.content }}
          </span>
        </div>
        <div v-if="logs.length > 0" class="inline-block w-1.5 h-3.5 bg-[#52c41a] animate-pulse ml-1 align-middle"></div>
      </div>
    </div>
  </PageCard>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import PageCard from "@/components/PageCard.vue"
import * as echarts from 'echarts'
import axios from 'axios'

const devices = ref([])
const aiStatus = ref(null)
const logs = ref([])
const autoRefresh = ref(true)
let refreshInterval = null

const stats = ref({ totalDevices: 0, onlineDevices: 0, runningTasks: 0, successRate: 100 })

const cpuMemChartRef = ref(null)
const fpsChartRef = ref(null)
let cpuMemChartInstance = null
let fpsChartInstance = null

onMounted(async () => {
  await fetchData()
  initCharts()
  if (autoRefresh.value) refreshInterval = setInterval(fetchData, 5000)
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
  if (cpuMemChartInstance) { cpuMemChartInstance.dispose(); cpuMemChartInstance = null }
  if (fpsChartInstance) { fpsChartInstance.dispose(); fpsChartInstance = null }
})

async function fetchData() {
  try {
    const devicesRes = await axios.get('/api/v1/devices')
    devices.value = devicesRes.data.data || []

    const total = devices.value.length
    const online = devices.value.filter(d => d.status === 'online' || d.status === 'busy').length
    stats.value.totalDevices = total
    stats.value.onlineDevices = online
    stats.value.runningTasks = devices.value.filter(d => d.status === 'busy').length

    const aiRes = await axios.get('/api/v1/ai/status')
    aiStatus.value = aiRes.data.data

    updateCharts()
  } catch (error) {
    console.error('获取数据失败:', error)
  }
}

function initCharts() {
  const lightTheme = (isFps = false) => ({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e8e8e8',
      textStyle: { color: '#1f1f1f', fontSize: 12 }
    },
    legend: {
      data: isFps ? ['FPS'] : ['CPU (%)', '内存 (%)'],
      textStyle: { color: '#666', fontSize: 11 },
      icon: 'roundRect'
    },
    grid: { left: 50, right: 20, top: 40, bottom: 30 },
    xAxis: {
      type: 'time',
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisLabel: { color: '#999', fontSize: 10 },
      splitLine: { show: false }
    },
    yAxis: isFps ? {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { color: '#999', fontSize: 10 },
      splitLine: { lineStyle: { color: '#f0f0f0' } }
    } : {
      type: 'value',
      max: 100,
      axisLine: { show: false },
      axisLabel: { color: '#999', fontSize: 10 },
      splitLine: { lineStyle: { color: '#f0f0f0' } }
    }
  })

  if (cpuMemChartRef.value) {
    cpuMemChartInstance = echarts.init(cpuMemChartRef.value)
    cpuMemChartInstance.setOption({
      ...lightTheme(),
      series: [
        { name: 'CPU (%)', type: 'line', smooth: true, symbol: 'none', lineStyle: { color: '#1677ff', width: 2 }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(22,119,255,0.12)' }, { offset: 1, color: 'rgba(22,119,255,0)' }]) }, data: [] },
        { name: '内存 (%)', type: 'line', smooth: true, symbol: 'none', lineStyle: { color: '#52c41a', width: 2 }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(82,196,26,0.12)' }, { offset: 1, color: 'rgba(82,196,26,0)' }]) }, data: [] }
      ]
    })
  }

  if (fpsChartRef.value) {
    fpsChartInstance = echarts.init(fpsChartRef.value)
    fpsChartInstance.setOption({
      ...lightTheme(true),
      series: [{
        name: 'FPS', type: 'line', smooth: true, symbol: 'none', lineStyle: { color: '#722ed1', width: 2 }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(114,46,209,0.12)' }, { offset: 1, color: 'rgba(114,46,209,0)' }]) }, data: []
      }]
    })
  }
}

function updateCharts() {
  const now = new Date()
  if (cpuMemChartInstance) {
    try {
      const option = cpuMemChartInstance.getOption()
      option.series[0].data.push([now, Math.random() * 100])
      option.series[1].data.push([now, Math.random() * 100])
      if (option.series[0].data.length > 30) { option.series[0].data.shift(); option.series[1].data.shift() }
      cpuMemChartInstance.setOption(option)
    } catch (e) { console.error('更新CPU图表失败:', e) }
  }
  if (fpsChartInstance) {
    try {
      const option = fpsChartInstance.getOption()
      option.series[0].data.push([now, Math.random() * 60])
      if (option.series[0].data.length > 30) option.series[0].data.shift()
      fpsChartInstance.setOption(option)
    } catch (e) { console.error('更新FPS图表失败:', e) }
  }
}

function refreshData() { fetchData() }

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) refreshInterval = setInterval(fetchData, 5000)
  else clearInterval(refreshInterval)
}

async function takeScreenshot(deviceId) {
  try {
    await axios.post(`/api/v1/devices/${deviceId}/screenshot`)
  } catch (e) {
    console.error('截屏失败:', e)
  }
}

function formatTime(isoString) {
  if (!isoString) return '-'
  return new Date(isoString).toLocaleTimeString('zh-CN')
}

function statusBadgeClass(status) {
  if (status === 'online') return 'badge-success'
  if (status === 'busy') return 'badge-warning'
  return 'badge-danger'
}

function statusLabel(status) {
  const labels = { online: '在线', busy: '忙碌', offline: '离线' }
  return labels[status] || status
}
</script>

<style scoped>
/* 统计卡片 */
.stat-card {
  @apply bg-white rounded-lg relative overflow-hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
.stat-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  border-radius: 0 2px 2px 0;
}
.stat-card-body {
  @apply p-4;
}
.stat-trend {
  @apply flex items-center gap-0.5 text-xs mt-1;
}
.stat-trend.up { color: #52c41a; }
</style>
