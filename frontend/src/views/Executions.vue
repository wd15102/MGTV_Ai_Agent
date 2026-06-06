<template>
  <div class="space-y-6">
    <!-- 标题 -->
    <div class="flex justify-between items-center">
      <h2 class="text-3xl font-bold text-gray-900">▶️ 执行控制</h2>
      <button @click="refreshExecutions" class="btn-primary">🔄 刷新</button>
    </div>

    <!-- 创建执行 -->
    <div class="card">
      <h3 class="card-title">🚀 执行测试用例</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <select v-model="newExecution.case_id" class="select-field">
          <option value="">选择用例...</option>
          <option v-for="c in cases" :key="c.id" :value="c.id">
            {{ c.name }} ({{ typeLabel(c.type) }})
          </option>
        </select>
        <select v-model="newExecution.device_id" class="select-field">
          <option value="">选择设备...</option>
          <option v-for="d in devices" :key="d.device_id" :value="d.device_id">
            {{ d.name }} ({{ d.device_id }})
          </option>
        </select>
        <button @click="executeCase" class="btn-primary" :disabled="!canExecute">
          执行
        </button>
      </div>
    </div>

    <!-- 执行列表 -->
    <div class="card">
      <h3 class="card-title">📋 执行记录</h3>
      <div class="table-container">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>用例</th>
              <th>设备</th>
              <th>状态</th>
              <th>开始时间</th>
              <th>结束时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="exec in executions" :key="exec.id">
              <td>{{ exec.id }}</td>
              <td class="font-medium text-gray-900">{{ getCaseName(exec.case_id) }}</td>
              <td>{{ getDeviceName(exec.device_id) }}</td>
              <td>
                <span :class="statusBadgeClass(exec.status)" class="badge">
                  {{ statusLabel(exec.status) }}
                </span>
              </td>
              <td class="text-sm">{{ formatTime(exec.start_time) }}</td>
              <td class="text-sm">{{ formatTime(exec.end_time) }}</td>
              <td>
                <button @click="viewExecution(exec)" class="text-blue-600 hover:text-blue-800 text-sm">
                  查看
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 执行详情模态框 -->
    <div v-if="selectedExecution" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-xl p-6 w-full max-w-4xl max-h-screen overflow-y-auto">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-xl font-bold">执行详情 #{{ selectedExecution.id }}</h3>
          <button @click="selectedExecution = null" class="text-gray-500 hover:text-gray-700">
            ✕
          </button>
        </div>

        <div class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div class="stat-box">
              <p class="stat-label">状态</p>
              <p :class="statusClass(selectedExecution.status)" class="stat-value">
                {{ statusLabel(selectedExecution.status) }}
              </p>
            </div>
            <div class="stat-box">
              <p class="stat-label">执行时间</p>
              <p class="stat-value text-sm">
                {{ formatTime(selectedExecution.start_time) }} - {{ formatTime(selectedExecution.end_time) }}
              </p>
            </div>
          </div>

          <!-- 错误信息 -->
          <div v-if="selectedExecution.error_message" class="bg-red-50 border border-red-200 rounded-lg p-4">
            <p class="text-sm font-medium text-red-800">错误信息：</p>
            <pre class="text-xs text-red-600 mt-2 overflow-x-auto">{{ selectedExecution.error_message }}</pre>
          </div>

          <!-- 截图 -->
          <div v-if="selectedExecution.screenshot_path">
            <p class="text-sm font-medium text-gray-700 mb-2">异常截图：</p>
            <img :src="'/api/v1/files/' + selectedExecution.screenshot_path" 
                 alt="截图" class="w-full rounded-lg shadow" />
          </div>

          <!-- 视频 -->
          <div v-if="selectedExecution.video_path">
            <p class="text-sm font-medium text-gray-700 mb-2">异常视频：</p>
            <video controls class="w-full">
              <source :src="'/api/v1/files/' + selectedExecution.video_path" type="video/mp4" />
            </video>
          </div>

          <!-- AI 分析 -->
          <div v-if="selectedExecution.ai_analysis">
            <p class="text-sm font-medium text-gray-700 mb-2">AI 分析：</p>
            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p class="text-sm text-blue-800">{{ selectedExecution.ai_analysis }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { useToast } from 'vue-toastification'

const toast = useToast()

const executions = ref([])
const cases = ref([])
const devices = ref([])
const selectedExecution = ref(null)
const newExecution = ref({ case_id: '', device_id: '' })

const canExecute = computed(() => newExecution.value.case_id && newExecution.value.device_id)

async function refreshExecutions() {
  try {
    const res = await axios.get('/api/v1/executions')
    executions.value = res.data.data || []
  } catch (error) {
    toast.error('加载执行记录失败: ' + error.message)
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

async function executeCase() {
  if (!canExecute.value) return
  
  try {
    const res = await axios.post('/api/v1/executions', newExecution.value)
    if (res.data.success) {
      toast.success('执行已开始，ID: ' + res.data.execution_id)
      newExecution.value = { case_id: '', device_id: '' }
      await refreshExecutions()
    }
  } catch (error) {
    toast.error('执行失败: ' + error.message)
  }
}

async function viewExecution(exec) {
  try {
    const res = await axios.get(`/api/v1/executions/${exec.id}`)
    selectedExecution.value = res.data.data
  } catch (error) {
    toast.error('加载执行详情失败: ' + error.message)
  }
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

function typeLabel(type) {
  const labels = { python: 'Python', yaml: 'YAML', natural: '自然语言' }
  return labels[type] || type
}

function formatTime(isoString) {
  if (!isoString) return '-'
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  refreshExecutions()
  loadCases()
  loadDevices()
})
</script>
