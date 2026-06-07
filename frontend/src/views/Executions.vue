<template>
  <PageCard title="执行控制" class="page-card-wrap">
    <!-- 标题 -->
    <div class="flex justify-between items-center">
      <div>
        <h2 class="text-lg font-semibold text-[#1f1f1f]">执行控制</h2>
        <p class="text-xs text-[#999] mt-0.5">EXECUTION CONTROL</p>
      </div>
      <button @click="refreshExecutions" class="btn-primary text-xs px-3 py-1.5">
        <svg class="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
        刷新
      </button>
    </div>

    <!-- 创建执行 -->
    <div class="card">
      <h3 class="card-title flex items-center gap-2">
        <svg class="w-4 h-4 text-[#1677ff]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
        执行测试用例
      </h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <select v-model="newExecution.case_id" class="select-field text-sm">
          <option value="">选择用例...</option>
          <option v-for="c in cases" :key="c.id" :value="c.id">{{ c.name }} ({{ typeLabel(c.type) }})</option>
        </select>
        <select v-model="newExecution.device_id" class="select-field text-sm">
          <option value="">选择设备...</option>
          <option v-for="d in devices" :key="d.device_id" :value="d.device_id">{{ d.name }} ({{ d.device_id }})</option>
        </select>
        <button @click="executeCase" class="btn-primary text-xs" :disabled="!canExecute">
          <svg class="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          执行
        </button>
      </div>
    </div>

    <!-- 执行列表 -->
    <div class="card p-0 overflow-hidden">
      <div class="px-4 py-3 border-b border-gray-50">
        <h3 class="card-title mb-0 flex items-center gap-2">
          <svg class="w-4 h-4 text-[#1677ff]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg>
          执行记录
        </h3>
      </div>
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
              <td class="font-mono text-[#999] text-xs">{{ exec.id }}</td>
              <td class="font-medium text-[#1f1f1f]">{{ getCaseName(exec.case_id) }}</td>
              <td class="text-[#666] text-xs">{{ getDeviceName(exec.device_id) }}</td>
              <td>
                <span :class="statusBadgeClass(exec.status)" class="badge text-[10px]">{{ statusLabel(exec.status) }}</span>
              </td>
              <td class="font-mono text-xs text-[#999]">{{ formatTime(exec.start_time) }}</td>
              <td class="font-mono text-xs text-[#999]">{{ formatTime(exec.end_time) }}</td>
              <td>
                <button @click="viewExecution(exec)" class="btn-text text-xs px-2 py-1">查看</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 执行详情模态框 -->
    <Teleport to="body">
      <div v-if="selectedExecution" class="modal-overlay" @click.self="selectedExecution = null">
        <div class="modal-content max-w-4xl">
          <div class="modal-header">
            <h3 class="text-base font-semibold text-[#1f1f1f]">执行详情 #{{ selectedExecution.id }}</h3>
            <button @click="selectedExecution = null" class="p-1 rounded hover:bg-gray-50 text-[#999] hover:text-[#1f1f1f] transition-colors">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
          <div class="modal-body space-y-4">
            <div class="grid grid-cols-2 gap-3">
              <div class="bg-[#fafafa] rounded p-3">
                <p class="text-[10px] text-[#999] uppercase">状态</p>
                <p class="text-sm font-bold font-mono mt-0.5" :class="statusColor(selectedExecution.status)">{{ statusLabel(selectedExecution.status) }}</p>
              </div>
              <div class="bg-[#fafafa] rounded p-3">
                <p class="text-[10px] text-[#999] uppercase">执行时间</p>
                <p class="text-xs font-mono text-[#666] mt-0.5">{{ formatTime(selectedExecution.start_time) }} — {{ formatTime(selectedExecution.end_time) }}</p>
              </div>
            </div>
            <div v-if="selectedExecution.error_message" class="rounded-lg p-3 bg-[#fff2f0] border border-[#ffccc7]">
              <p class="text-xs font-semibold text-[#ff4d4f] mb-1">⚠️ 错误信息：</p>
              <pre class="text-[11px] text-[#d9363e] font-mono overflow-x-auto">{{ selectedExecution.error_message }}</pre>
            </div>
            <div v-if="selectedExecution.screenshot_path">
              <p class="text-xs font-semibold text-[#666] mb-1.5">📷 异常截图：</p>
              <img :src="'/api/v1/files/' + selectedExecution.screenshot_path" alt="截图" class="w-full rounded-lg border border-gray-100" />
            </div>
            <div v-if="selectedExecution.video_path">
              <p class="text-xs font-semibold text-[#666] mb-1.5">🎥 异常视频：</p>
              <video controls class="w-full rounded-lg border border-gray-100">
                <source :src="'/api/v1/files/' + selectedExecution.video_path" type="video/mp4" />
              </video>
            </div>
            <div v-if="selectedExecution.ai_analysis" class="rounded-lg p-3 bg-[#f0f5ff] border border-[#d6e4ff]">
              <p class="text-xs font-semibold text-[#1677ff] mb-1">🤖 AI 分析：</p>
              <p class="text-xs text-[#1f1f1f]">{{ selectedExecution.ai_analysis }}</p>
            </div>
          </div>
          <div class="modal-footer">
            <button @click="selectedExecution = null" class="btn-secondary text-xs">关闭</button>
          </div>
        </div>
      </div>
    </Teleport>
  </PageCard>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import PageCard from "@/components/PageCard.vue"
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
  try { const res = await axios.get('/api/v1/executions'); executions.value = res.data.data || [] }
  catch (error) { toast.error('加载执行记录失败: ' + error.message) }
}

async function loadCases() {
  try { const res = await axios.get('/api/v1/cases'); cases.value = res.data.data || [] }
  catch (error) { console.error('加载用例失败:', error) }
}

async function loadDevices() {
  try { const res = await axios.get('/api/v1/devices'); devices.value = res.data.data || [] }
  catch (error) { console.error('加载设备失败:', error) }
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
  } catch (error) { toast.error('执行失败: ' + error.message) }
}

async function viewExecution(exec) {
  try { const res = await axios.get(`/api/v1/executions/${exec.id}`); selectedExecution.value = res.data.data }
  catch (error) { toast.error('加载执行详情失败: ' + error.message) }
}

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
function typeLabel(type) { return { python: 'Python', yaml: 'YAML', natural: '自然语言' }[type] || type }
function formatTime(isoString) {
  if (!isoString) return '-'
  return new Date(isoString).toLocaleString('zh-CN')
}

onMounted(() => { refreshExecutions(); loadCases(); loadDevices() })
</script>
