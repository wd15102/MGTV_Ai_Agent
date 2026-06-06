<template>
  <div class="space-y-6">
    <!-- 标题 -->
    <div class="flex justify-between items-center">
      <h2 class="text-3xl font-bold text-gray-900">📄 测试报告</h2>
      <div class="flex space-x-2">
        <button @click="loadReports" class="btn-primary">🔄 刷新</button>
        <button v-if="selectedReport" @click="exportReport" class="btn-secondary">
          📥 导出
        </button>
      </div>
    </div>

    <!-- 报告列表 -->
    <div class="card">
      <div v-if="reports.length === 0" class="text-center py-8 text-gray-500">
        暂无报告，请先执行测试用例
      </div>
      
      <div v-else class="table-container">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>用例</th>
              <th>设备</th>
              <th>状态</th>
              <th>开始时间</th>
              <th>耗时</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="report in reports" :key="report.id" 
                class="cursor-pointer hover:bg-gray-50"
                @click="viewReport(report)">
              <td>{{ report.id }}</td>
              <td class="font-medium text-gray-900">{{ getCaseName(report.case_id) }}</td>
              <td>{{ getDeviceName(report.device_id) }}</td>
              <td>
                <span :class="statusBadgeClass(report.status)" class="badge">
                  {{ statusLabel(report.status) }}
                </span>
              </td>
              <td class="text-sm">{{ formatTime(report.start_time) }}</td>
              <td class="text-sm">{{ calculateDuration(report.start_time, report.end_time) }}</td>
              <td>
                <button @click.stop="viewReport(report)" class="text-blue-600 hover:text-blue-800 text-sm">
                  查看详情
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 报告详情 -->
    <div v-if="selectedReport" class="card">
      <div class="flex justify-between items-center mb-4">
        <h3 class="card-title">📊 报告详情 #{{ selectedReport.id }}</h3>
        <button @click="selectedReport = null" class="text-gray-500 hover:text-gray-700">
          ✕
        </button>
      </div>

      <!-- 基本信息 -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div class="stat-box">
          <p class="stat-label">状态</p>
          <p :class="statusClass(selectedReport.status)" class="stat-value">
            {{ statusLabel(selectedReport.status) }}
          </p>
        </div>
        <div class="stat-box">
          <p class="stat-label">用例</p>
          <p class="stat-value text-sm">{{ getCaseName(selectedReport.case_id) }}</p>
        </div>
        <div class="stat-box">
          <p class="stat-label">设备</p>
          <p class="stat-value text-sm">{{ getDeviceName(selectedReport.device_id) }}</p>
        </div>
        <div class="stat-box">
          <p class="stat-label">耗时</p>
          <p class="stat-value">{{ calculateDuration(selectedReport.start_time, selectedReport.end_time) }}</p>
        </div>
      </div>

      <!-- 错误信息 -->
      <div v-if="selectedReport.error_message" class="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
        <p class="text-sm font-medium text-red-800 mb-2">错误信息：</p>
        <pre class="text-xs text-red-600 overflow-x-auto">{{ selectedReport.error_message }}</pre>
      </div>

      <!-- 性能图表 -->
      <div v-if="performanceData.length > 0" class="mb-6">
        <h4 class="text-lg font-semibold mb-2">📈 性能曲线</h4>
        <div ref="perfChart" class="chart-container"></div>
      </div>

      <!-- 日志 -->
      <div v-if="logs.length > 0" class="mb-6">
        <h4 class="text-lg font-semibold mb-2">📋 日志</h4>
        <div class="bg-gray-900 text-green-400 font-mono text-sm p-4 rounded-lg h-64 overflow-y-auto">
          <div v-for="(log, idx) in logs" :key="idx" class="mb-1">
            <span class="text-gray-500">{{ log.timestamp }}</span>
            <span :class="log.level === 'ERROR' ? 'text-red-400' : 'text-green-400'">
              {{ log.message }}
            </span>
          </div>
        </div>
      </div>

      <!-- 截图 -->
      <div v-if="selectedReport.screenshot_path">
        <h4 class="text-lg font-semibold mb-2">📷 异常截图</h4>
        <img :src="'/api/v1/files/' + selectedReport.screenshot_path" 
             alt="截图" class="w-full rounded-lg shadow" />
      </div>

      <!-- 视频 -->
      <div v-if="selectedReport.video_path" class="mt-6">
        <h4 class="text-lg font-semibold mb-2">🎥 异常视频</h4>
        <video controls class="w-full">
          <source :src="'/api/v1/files/' + selectedReport.video_path" type="video/mp4" />
        </video>
      </div>

      <!-- AI 分析 -->
      <div v-if="selectedReport.ai_analysis" class="mt-6">
        <h4 class="text-lg font-semibold mb-2">🤖 AI 分析</h4>
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p class="text-sm text-blue-800">{{ selectedReport.ai_analysis }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'
import { useToast } from 'vue-toastification'

const toast = useToast()

const reports = ref([])
const selectedReport = ref(null)
const performanceData = ref([])
const logs = ref([])
const cases = ref([])
const devices = ref([])

let perfChartInstance = null

onMounted(async () => {
  await loadReports()
  await loadCases()
  await loadDevices()
})

async function loadReports() {
  try {
    // 获取执行记录作为报告
    const res = await axios.get('/api/v1/executions')
    reports.value = res.data.data || []
    toast.success('报告列表已刷新')
  } catch (error) {
    toast.error('加载报告失败: ' + error.message)
  }
}

async function loadCases() {
  try {
    const res = await axios.get('/api/v1/cases')
    cases.value = res.data.data || []
  } catch (error) {
    console.error('加载用例失败:', error)
  }
}

async function loadDevices() {
  try {
    const res = await axios.get('/api/v1/devices')
    devices.value = res.data.data || []
  } catch (error) {
    console.error('加载设备失败:', error)
  }
}

async function viewReport(report) {
  try {
    const res = await axios.get(`/api/v1/reports/${report.id}`)
    selectedReport.value = res.data.data.execution
    performanceData.value = res.data.data.performance || []
    logs.value = res.data.data.logs || []
    
    // 渲染性能图表
    await nextTick()
    renderPerfChart()
  } catch (error) {
    toast.error('加载报告详情失败: ' + error.message)
  }
}

function renderPerfChart() {
  const chartEl = document.querySelector('[ref="perfChart"]')
  if (!chartEl || performanceData.value.length === 0) return
  
  if (perfChartInstance) {
    perfChartInstance.dispose()
  }
  
  perfChartInstance = echarts.init(chartEl)
  
  const times = performanceData.value.map(d => d.timestamp)
  const cpuData = performanceData.value.map(d => d.cpu_usage)
  const memData = performanceData.value.map(d => d.memory_percent)
  const fpsData = performanceData.value.map(d => d.fps)
  
  perfChartInstance.setOption({
    title: { text: '性能监控' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['CPU (%)', '内存 (%)', 'FPS'] },
    xAxis: { type: 'category', data: times },
    yAxis: { type: 'value' },
    series: [
      { name: 'CPU (%)', type: 'line', data: cpuData },
      { name: '内存 (%)', type: 'line', data: memData },
      { name: 'FPS', type: 'line', yAxisIndex: 1, data: fpsData }
    ]
  })
}

function exportReport() {
  // 导出为 HTML 报告
  toast.info('导出功能开发中...')
}

function getCaseName(caseId) {
  const c = cases.value.find(x => x.id === caseId)
  return c ? c.name : `用例#${caseId}`
}

function getDeviceName(deviceId) {
  const d = devices.value.find(x => x.id === deviceId)
  return d ? d.name : `设备#${deviceId}`
}

function statusLabel(status) {
  const labels = {
    'pending': '等待中',
    'running': '执行中',
    'success': '成功',
    'failed': '失败',
    'timeout': '超时'
  }
  return labels[status] || status
}

function statusBadgeClass(status) {
  return {
    'badge-success': status === 'success',
    'badge-warning': status === 'running' || status === 'pending',
    'badge-danger': status === 'failed' || status === 'timeout'
  }
}

function statusClass(status) {
  return {
    'text-green-600': status === 'success',
    'text-yellow-600': status === 'running' || status === 'pending',
    'text-red-600': status === 'failed' || status === 'timeout'
  }
}

function formatTime(isoString) {
  if (!isoString) return '-'
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN')
}

function calculateDuration(start, end) {
  if (!start || !end) return '-'
  const startDate = new Date(start)
  const endDate = new Date(end)
  const seconds = Math.floor((endDate - startDate) / 1000)
  
  if (seconds < 60) return `${seconds}秒`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}分${remainingSeconds}秒`
}
</script>
