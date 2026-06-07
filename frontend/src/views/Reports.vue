<template>
  <PageCard title="测试报告" class="page-card-wrap">
    <!-- 标题 -->
    <div class="flex justify-between items-center">
      <div>
        <h2 class="text-lg font-semibold text-[#1f1f1f]">测试报告</h2>
        <p class="text-xs text-[#999] mt-0.5">TEST REPORTS</p>
      </div>
      <div class="flex gap-2">
        <button @click="loadReports" class="btn-primary text-xs px-3 py-1.5">
          <svg class="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
          刷新
        </button>
        <button v-if="selectedReport" @click="exportReport" class="btn-secondary text-xs px-3 py-1.5">导出</button>
      </div>
    </div>

    <!-- 报告列表 -->
    <div class="card p-0 overflow-hidden">
      <div v-if="reports.length === 0" class="text-center py-12 text-[#999]">
        <svg class="w-12 h-12 mx-auto text-[#d9d9d9] mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
        <p class="text-sm">暂无报告，请先执行测试用例</p>
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
            <tr v-for="report in reports" :key="report.id" class="cursor-pointer" @click="viewReport(report)">
              <td class="font-mono text-[#999] text-xs">{{ report.id }}</td>
              <td class="font-medium text-[#1f1f1f]">{{ getCaseName(report.case_id) }}</td>
              <td class="text-[#666] text-xs">{{ getDeviceName(report.device_id) }}</td>
              <td><span :class="statusBadgeClass(report.status)" class="badge text-[10px]">{{ statusLabel(report.status) }}</span></td>
              <td class="font-mono text-xs text-[#999]">{{ formatTime(report.start_time) }}</td>
              <td class="font-mono text-xs text-[#999]">{{ calculateDuration(report.start_time, report.end_time) }}</td>
              <td><button @click.stop="viewReport(report)" class="btn-text text-xs px-2 py-1">查看详情</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 报告详情 -->
    <div v-if="selectedReport" class="card">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-base font-semibold mb-0">报告详情 #{{ selectedReport.id }}</h3>
        <button @click="closeReport" class="p-1 rounded hover:bg-gray-50 text-[#999] hover:text-[#1f1f1f] transition-colors">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
      </div>

      <!-- 基本信息 -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div class="bg-[#fafafa] rounded p-3 border-l-4 border-l-[#1677ff]">
          <p class="text-[10px] text-[#999] uppercase">状态</p>
          <p class="text-sm font-bold font-mono mt-0.5" :class="statusColor(selectedReport.status)">{{ statusLabel(selectedReport.status) }}</p>
        </div>
        <div class="bg-[#fafafa] rounded p-3 border-l-4 border-l-[#52c41a]">
          <p class="text-[10px] text-[#999] uppercase">用例</p>
          <p class="text-xs font-mono text-[#1f1f1f] mt-0.5">{{ getCaseName(selectedReport.case_id) }}</p>
        </div>
        <div class="bg-[#fafafa] rounded p-3 border-l-4 border-l-[#722ed1]">
          <p class="text-[10px] text-[#999] uppercase">设备</p>
          <p class="text-xs font-mono text-[#1f1f1f] mt-0.5">{{ getDeviceName(selectedReport.device_id) }}</p>
        </div>
        <div class="bg-[#fafafa] rounded p-3 border-l-4 border-l-[#faad14]">
          <p class="text-[10px] text-[#999] uppercase">耗时</p>
          <p class="text-sm font-bold font-mono text-[#1f1f1f] mt-0.5">{{ calculateDuration(selectedReport.start_time, selectedReport.end_time) }}</p>
        </div>
      </div>

      <div v-if="selectedReport.error_message" class="mb-4 rounded-lg p-3 bg-[#fff2f0] border border-[#ffccc7]">
        <p class="text-xs font-semibold text-[#ff4d4f] mb-1">⚠️ 错误信息：</p>
        <pre class="text-[11px] text-[#d9363e] font-mono overflow-x-auto">{{ selectedReport.error_message }}</pre>
      </div>

      <div v-if="performanceData.length > 0" class="mb-4">
        <h4 class="text-sm font-semibold text-[#1f1f1f] mb-2">📈 性能曲线</h4>
        <div ref="perfChartRef" class="chart-container"></div>
      </div>

      <div v-if="logs.length > 0" class="mb-4">
        <h4 class="text-sm font-semibold text-[#1f1f1f] mb-2">📋 日志</h4>
        <div class="bg-[#1a1b2e] rounded-lg h-48 overflow-y-auto p-3 font-mono text-xs">
          <div v-for="(log, idx) in logs" :key="idx" class="mb-1 leading-relaxed">
            <span class="text-[rgba(255,255,255,0.3)]">[{{ log.timestamp }}]</span>
            <span :class="log.level === 'ERROR' ? 'text-[#ff4d4f]' : 'text-[#52c41a]'">{{ log.message }}</span>
          </div>
          <div v-if="logs.length > 0" class="inline-block w-1.5 h-3.5 bg-[#52c41a] animate-pulse ml-1 align-middle"></div>
        </div>
      </div>

      <div v-if="selectedReport.screenshot_path" class="mb-4">
        <h4 class="text-sm font-semibold text-[#1f1f1f] mb-2">📷 异常截图</h4>
        <img :src="'/api/v1/files/' + selectedReport.screenshot_path" alt="截图" class="w-full rounded-lg border border-gray-100" />
      </div>
      <div v-if="selectedReport.video_path" class="mb-4">
        <h4 class="text-sm font-semibold text-[#1f1f1f] mb-2">🎥 异常视频</h4>
        <video controls class="w-full rounded-lg border border-gray-100">
          <source :src="'/api/v1/files/' + selectedReport.video_path" type="video/mp4" />
        </video>
      </div>
      <div v-if="selectedReport.ai_analysis" class="rounded-lg p-3 bg-[#f0f5ff] border border-[#d6e4ff]">
        <h4 class="text-xs font-semibold text-[#1677ff] mb-1">🤖 AI 分析</h4>
        <p class="text-xs text-[#1f1f1f]">{{ selectedReport.ai_analysis }}</p>
      </div>
    </div>
  </PageCard>
</template>

<script setup>
import { ref, onMounted, nextTick, onUnmounted } from 'vue'
import PageCard from "@/components/PageCard.vue"
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
const perfChartRef = ref(null)
let perfChartInstance = null

onMounted(async () => { await loadReports(); await loadCases(); await loadDevices() })
onUnmounted(() => { if (perfChartInstance) { perfChartInstance.dispose(); perfChartInstance = null } })

function closeReport() {
  selectedReport.value = null; performanceData.value = []; logs.value = []
  if (perfChartInstance) { perfChartInstance.dispose(); perfChartInstance = null }
}

async function loadReports() {
  try { const res = await axios.get('/api/v1/executions'); reports.value = res.data.data || [] } catch (error) { toast.error('加载报告失败: ' + error.message) }
}
async function loadCases() { try { const res = await axios.get('/api/v1/cases'); cases.value = res.data.data || [] } catch (e) { console.error(e) } }
async function loadDevices() { try { const res = await axios.get('/api/v1/devices'); devices.value = res.data.data || [] } catch (e) { console.error(e) } }

async function viewReport(report) {
  try {
    const res = await axios.get(`/api/v1/reports/${report.id}`)
    selectedReport.value = res.data.data.execution
    performanceData.value = res.data.data.performance || []
    logs.value = res.data.data.logs || []
    await nextTick()
    renderPerfChart()
  } catch (error) { toast.error('加载报告详情失败: ' + error.message) }
}

function renderPerfChart() {
  if (!perfChartRef.value || performanceData.value.length === 0) return
  if (perfChartInstance) perfChartInstance.dispose()

  perfChartInstance = echarts.init(perfChartRef.value)
  const times = performanceData.value.map(d => d.timestamp)
  const cpuData = performanceData.value.map(d => d.cpu_usage)
  const memData = performanceData.value.map(d => d.memory_percent)
  const fpsData = performanceData.value.map(d => d.fps)

  perfChartInstance.setOption({
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: '#e8e8e8', textStyle: { color: '#1f1f1f', fontSize: 11 } },
    legend: { data: ['CPU (%)', '内存 (%)', 'FPS'], textStyle: { color: '#666', fontSize: 11 }, icon: 'roundRect' },
    grid: { left: 50, right: 25, top: 45, bottom: 30 },
    xAxis: { type: 'category', data: times, axisLabel: { color: '#999', fontSize: 9, rotate: 30 }, axisLine: { lineStyle: { color: '#e8e8e8' } }, splitLine: { show: false } },
    yAxis: [
      { type: 'value', name: '%', nameTextStyle: { color: '#999', fontSize: 9 }, axisLabel: { color: '#999', fontSize: 9 }, splitLine: { lineStyle: { color: '#f0f0f0' } }, axisLine: { show: false } },
      { type: 'value', name: 'FPS', nameTextStyle: { color: '#999', fontSize: 9 }, axisLabel: { color: '#999', fontSize: 9 }, splitLine: { show: false }, axisLine: { show: false } }
    ],
    series: [
      { name: 'CPU (%)', type: 'line', smooth: true, symbol: 'none', lineStyle: { color: '#1677ff', width: 2 }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(22,119,255,0.12)' }, { offset: 1, color: 'rgba(22,119,255,0)' }]) }, data: cpuData },
      { name: '内存 (%)', type: 'line', smooth: true, symbol: 'none', lineStyle: { color: '#52c41a', width: 2 }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(82,196,26,0.12)' }, { offset: 1, color: 'rgba(82,196,26,0)' }]) }, data: memData },
      { name: 'FPS', type: 'line', smooth: true, symbol: 'none', yAxisIndex: 1, lineStyle: { color: '#722ed1', width: 2 }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(114,46,209,0.12)' }, { offset: 1, color: 'rgba(114,46,209,0)' }]) }, data: fpsData }
    ]
  })
}

function exportReport() { toast.info('导出功能开发中...') }
function getCaseName(caseId) { const c = cases.value.find(x => x.id === caseId); return c ? c.name : `用例#${caseId}` }
function getDeviceName(deviceId) { const d = devices.value.find(x => x.id === deviceId); return d ? d.name : `设备#${deviceId}` }
function statusLabel(status) { return { pending: '等待中', running: '执行中', success: '成功', failed: '失败', timeout: '超时' }[status] || status }
function statusBadgeClass(status) {
  if (status === 'success') return 'badge-success'
  if (status === 'running' || status === 'pending') return 'badge-warning'
  return 'badge-danger'
}
function statusColor(status) {
  if (status === 'success') return 'text-[#52c41a]'
  if (status === 'running') return 'text-[#faad14]'
  if (status === 'pending') return 'text-[#999]'
  return 'text-[#ff4d4f]'
}
function formatTime(isoString) { if (!isoString) return '-'; return new Date(isoString).toLocaleString('zh-CN') }
function calculateDuration(start, end) {
  if (!start || !end) return '-'
  const seconds = Math.floor((new Date(end) - new Date(start)) / 1000)
  if (seconds < 60) return `${seconds}秒`
  return `${Math.floor(seconds / 60)}分${seconds % 60}秒`
}
</script>
