<template>
  <PageCard title="AI 状态" class="page-card-wrap">
    <!-- 标题 -->
    <div class="flex justify-between items-center">
      <div>
        <h2 class="text-lg font-semibold text-[#1f1f1f]">AI 状态</h2>
        <p class="text-xs text-[#999] mt-0.5">AI AGENT STATUS</p>
      </div>
      <button @click="refreshStatus" class="btn-primary text-xs px-3 py-1.5">
        <svg class="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
        刷新
      </button>
    </div>

    <!-- AI Agent 核心大脑 -->
    <div class="card">
      <div class="flex items-center gap-3 mb-5">
        <div class="w-9 h-9 rounded-lg bg-gradient-to-br from-[#1677ff] to-[#4096ff] flex items-center justify-center text-white text-sm font-bold shadow-sm">
          AI
        </div>
        <div>
          <h3 class="text-base font-semibold text-[#1f1f1f]">AI 决策大脑</h3>
          <p class="text-[10px] text-[#999] tracking-wider uppercase">DECISION ENGINE</p>
        </div>
      </div>

      <div v-if="aiStatus" class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div class="flex flex-col items-center p-4 rounded-lg bg-[#fafafa] border border-[#f0f0f0]">
          <div :class="'w-4 h-4 rounded-full mb-2 ' + (aiStatus.status === 'ready' ? 'bg-[#52c41a] shadow-[0_0_0_3px_rgba(82,196,26,0.15)]' : 'bg-[#d9d9d9]')"></div>
          <span class="text-lg font-bold font-mono" :class="aiStatus.status === 'ready' ? 'text-[#52c41a]' : 'text-[#999]'">{{ aiStatus.status }}</span>
          <span class="text-[10px] text-[#999] mt-0.5 uppercase">状态</span>
        </div>
        <div class="flex flex-col items-center justify-center p-4 rounded-lg bg-[#fafafa] border border-[#f0f0f0]">
          <span class="text-lg font-bold font-mono text-[#1677ff]">{{ aiStatus.current_task || '—' }}</span>
          <span class="text-[10px] text-[#999] mt-0.5 uppercase">当前任务</span>
        </div>
        <div class="flex flex-col items-center justify-center p-4 rounded-lg bg-[#fafafa] border border-[#f0f0f0]">
          <span class="text-lg font-bold font-mono text-[#722ed1]">{{ aiStatus.thought_history_len || 0 }}</span>
          <span class="text-[10px] text-[#999] mt-0.5 uppercase">思考记录</span>
        </div>
        <div class="flex flex-col items-center justify-center p-4 rounded-lg bg-[#fafafa] border border-[#f0f0f0]">
          <span class="text-lg font-bold font-mono text-[#52c41a]">{{ uptime }}</span>
          <span class="text-[10px] text-[#999] mt-0.5 uppercase">运行时间</span>
        </div>
      </div>
      <div v-else class="text-center py-8 text-[#999]">
        <div class="loading-spinner mx-auto mb-3"></div>
        <span class="text-xs animate-pulse">LOADING...</span>
      </div>
    </div>

    <!-- 模型状态 -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <!-- Qwen-VL -->
      <div class="card relative overflow-hidden">
        <div class="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-[#1677ff] to-transparent"></div>
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-[#f0f5ff] border border-[#d6e4ff] flex items-center justify-center text-sm">🌐</div>
            <div>
              <h4 class="text-sm font-semibold text-[#1f1f1f]">Qwen-VL-7B</h4>
              <p class="text-[9px] text-[#999] tracking-wider">VISION LANGUAGE MODEL</p>
            </div>
          </div>
          <span :class="qwenEnabled ? 'badge-success' : 'badge-danger'" class="text-[10px]">{{ qwenEnabled ? '启用' : '未启用' }}</span>
        </div>
        <div class="space-y-1.5 text-xs">
          <div class="flex justify-between py-1.5 px-2.5 rounded bg-[#fafafa]">
            <span class="text-[#999]">MODEL</span>
            <span class="text-[#666] truncate max-w-[160px]">{{ qwenConfig.model_path }}</span>
          </div>
          <div class="flex justify-between py-1.5 px-2.5 rounded bg-[#fafafa]">
            <span class="text-[#999]">QUANT</span>
            <span class="text-[#1677ff]">{{ qwenConfig.quantize }}</span>
          </div>
          <div class="flex justify-between py-1.5 px-2.5 rounded bg-[#fafafa]">
            <span class="text-[#999]">TIMEOUT</span>
            <span class="text-[#faad14]">{{ qwenConfig.timeout }}s</span>
          </div>
          <div class="flex justify-between py-1.5 px-2.5 rounded bg-[#fafafa]">
            <span class="text-[#999]">API</span>
            <span class="text-[#666] truncate max-w-[140px]">{{ qwenConfig.base_url }}</span>
          </div>
        </div>
        <button @click="testQwen" class="mt-3 w-full py-1.5 rounded border border-[#d6e4ff] text-xs text-[#1677ff] font-medium hover:bg-[#f0f5ff] transition-all">🧪 测试连接</button>
      </div>

      <!-- YOLOv8 -->
      <div class="card relative overflow-hidden">
        <div class="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-[#52c41a] to-transparent"></div>
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-[#f6ffed] border border-[#b7eb8f] flex items-center justify-center text-sm">🎯</div>
            <div>
              <h4 class="text-sm font-semibold text-[#1f1f1f]">YOLOv8</h4>
              <p class="text-[9px] text-[#999] tracking-wider">OBJECT DETECTION</p>
            </div>
          </div>
          <span :class="yoloEnabled ? 'badge-success' : 'badge-danger'" class="text-[10px]">{{ yoloEnabled ? '启用' : '未启用' }}</span>
        </div>
        <div class="space-y-1.5 text-xs">
          <div class="flex justify-between py-1.5 px-2.5 rounded bg-[#fafafa]">
            <span class="text-[#999]">MODEL</span>
            <span class="text-[#666] truncate max-w-[160px]">{{ yoloConfig.model_path }}</span>
          </div>
          <div class="flex justify-between py-1.5 px-2.5 rounded bg-[#fafafa]">
            <span class="text-[#999]">CONF</span>
            <span class="text-[#52c41a]">{{ yoloConfig.conf_threshold }}</span>
          </div>
          <div class="flex justify-between py-1.5 px-2.5 rounded bg-[#fafafa]">
            <span class="text-[#999]">ENABLED</span>
            <span :class="yoloConfig.enabled ? 'text-[#52c41a]' : 'text-[#ff4d4f]'">{{ yoloConfig.enabled ? 'YES' : 'NO' }}</span>
          </div>
        </div>
        <button class="mt-3 w-full py-1.5 rounded border border-[#b7eb8f] text-xs text-[#52c41a] font-medium hover:bg-[#f6ffed] transition-all">🧪 测试检测</button>
      </div>

      <!-- PaddleOCR -->
      <div class="card relative overflow-hidden">
        <div class="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-[#722ed1] to-transparent"></div>
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-[#f9f0ff] border border-[#d3adf7] flex items-center justify-center text-sm">📝</div>
            <div>
              <h4 class="text-sm font-semibold text-[#1f1f1f]">PaddleOCR</h4>
              <p class="text-[9px] text-[#999] tracking-wider">TEXT RECOGNITION</p>
            </div>
          </div>
          <span :class="ocrEnabled ? 'badge-success' : 'badge-danger'" class="text-[10px]">{{ ocrEnabled ? '启用' : '未启用' }}</span>
        </div>
        <div class="space-y-1.5 text-xs">
          <div class="flex justify-between py-1.5 px-2.5 rounded bg-[#fafafa]">
            <span class="text-[#999]">CONF</span>
            <span class="text-[#722ed1]">{{ ocrConfig.conf_threshold }}</span>
          </div>
          <div class="flex justify-between py-1.5 px-2.5 rounded bg-[#fafafa]">
            <span class="text-[#999]">ENABLED</span>
            <span :class="ocrConfig.enabled ? 'text-[#52c41a]' : 'text-[#ff4d4f]'">{{ ocrConfig.enabled ? 'YES' : 'NO' }}</span>
          </div>
          <div class="flex justify-between py-1.5 px-2.5 rounded bg-[#fafafa]">
            <span class="text-[#999]">LANG</span>
            <span class="text-[#1f1f1f]">中文</span>
          </div>
        </div>
        <button class="mt-3 w-full py-1.5 rounded border border-[#d3adf7] text-xs text-[#722ed1] font-medium hover:bg-[#f9f0ff] transition-all">🧪 测试识别</button>
      </div>
    </div>

    <!-- 降级策略 -->
    <div class="card">
      <h3 class="card-title flex items-center gap-2">
        <svg class="w-4 h-4 text-[#1677ff]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
        降级策略
        <span class="text-[10px] text-[#999] font-normal">FALLBACK STRATEGY</span>
      </h3>

      <div class="flex flex-wrap items-center justify-center gap-2 mb-4">
        <div :class="'flow-node ' + (qwenEnabled ? 'active' : 'inactive')">
          <div class="text-base mb-0.5">🌐</div>
          <div class="text-[10px] font-semibold">Qwen-VL</div>
          <div class="text-[8px] font-mono" :class="qwenEnabled ? 'text-[#52c41a]' : 'text-[#ff4d4f]'">{{ qwenEnabled ? 'ONLINE' : 'OFFLINE' }}</div>
        </div>
        <div class="flow-arrow">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/></svg>
        </div>
        <div :class="'flow-node ' + (uiAutomatorEnabled ? 'active' : 'inactive')">
          <div class="text-base mb-0.5">🤖</div>
          <div class="text-[10px] font-semibold">uiautomator2</div>
          <div class="text-[8px] font-mono" :class="uiAutomatorEnabled ? 'text-[#52c41a]' : 'text-[#ff4d4f]'">{{ uiAutomatorEnabled ? 'ONLINE' : 'OFFLINE' }}</div>
        </div>
        <div class="flow-arrow">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/></svg>
        </div>
        <div :class="'flow-node ' + (airtestEnabled ? 'active' : 'inactive')">
          <div class="text-base mb-0.5">🎮</div>
          <div class="text-[10px] font-semibold">Airtest</div>
          <div class="text-[8px] font-mono" :class="airtestEnabled ? 'text-[#52c41a]' : 'text-[#ff4d4f]'">{{ airtestEnabled ? 'ONLINE' : 'OFFLINE' }}</div>
        </div>
      </div>

      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div class="flex flex-col items-center p-3 rounded-lg bg-[#fafafa] border border-[#f0f0f0]">
          <span :class="fallbackEnabled ? 'text-[#52c41a]' : 'text-[#ff4d4f]'" class="text-base font-bold font-mono">{{ fallbackEnabled ? 'ON' : 'OFF' }}</span>
          <span class="text-[10px] text-[#999] mt-0.5 font-mono">降级开关</span>
        </div>
        <div class="flex flex-col items-center p-3 rounded-lg bg-[#fafafa] border border-[#f0f0f0]">
          <span :class="uiAutomatorEnabled ? 'text-[#1677ff]' : 'text-[#ff4d4f]'" class="text-base font-bold font-mono">{{ uiAutomatorEnabled ? 'ON' : 'OFF' }}</span>
          <span class="text-[10px] text-[#999] mt-0.5 font-mono">uiautomator2</span>
        </div>
        <div class="flex flex-col items-center p-3 rounded-lg bg-[#fafafa] border border-[#f0f0f0]">
          <span :class="airtestEnabled ? 'text-[#52c41a]' : 'text-[#ff4d4f]'" class="text-base font-bold font-mono">{{ airtestEnabled ? 'ON' : 'OFF' }}</span>
          <span class="text-[10px] text-[#999] mt-0.5 font-mono">Airtest</span>
        </div>
        <div class="flex flex-col items-center justify-center p-3 rounded-lg bg-[#f0f5ff] border border-[#d6e4ff]">
          <span class="text-[9px] text-[#1677ff] text-center leading-relaxed">Qwen → uiautomator → Airtest</span>
          <span class="text-[8px] text-[#999] mt-0.5 font-mono">降级链路</span>
        </div>
      </div>
    </div>

    <!-- 测试弹窗 -->
    <Teleport to="body">
      <div v-if="showTestModal" class="modal-overlay" @click.self="showTestModal = false">
        <div class="modal-content max-w-lg">
          <div class="modal-header">
            <h3 class="text-base font-semibold text-[#1f1f1f]">{{ testResult.title }}</h3>
            <button @click="showTestModal = false" class="p-1 rounded hover:bg-gray-50 text-[#999] hover:text-[#1f1f1f] transition-colors">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
          <div class="modal-body">
            <div class="bg-[#1a1b2e] rounded-lg p-4 font-mono text-xs">
              <pre class="text-[#52c41a] whitespace-pre-wrap">{{ testResult.message }}</pre>
            </div>
          </div>
          <div class="modal-footer">
            <button @click="showTestModal = false" class="btn-primary text-xs">关闭</button>
          </div>
        </div>
      </div>
    </Teleport>
  </PageCard>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import PageCard from "@/components/PageCard.vue"
import axios from 'axios'
import { useToast } from 'vue-toastification'

const toast = useToast()

const aiStatus = ref(null)
const qwenEnabled = ref(false)
const yoloEnabled = ref(false)
const ocrEnabled = ref(false)
const fallbackEnabled = ref(false)
const uiAutomatorEnabled = ref(false)
const airtestEnabled = ref(false)
const uptime = ref('00:00:00')
const showTestModal = ref(false)
const testResult = ref({ title: '', message: '' })
const qwenConfig = ref({ model_path: './models/qwen-vl-7b', quantize: 'INT4', timeout: 5, base_url: 'http://localhost:11434' })
const yoloConfig = ref({ model_path: './models/yolov8/best.pt', conf_threshold: 0.85, enabled: true })
const ocrConfig = ref({ conf_threshold: 0.5, enabled: true })
let uptimeInterval = null

onMounted(async () => { await refreshStatus(); startUptimeCounter() })
onUnmounted(() => { if (uptimeInterval) clearInterval(uptimeInterval) })

async function refreshStatus() {
  try {
    const res = await axios.get('/api/v1/ai/status')
    const data = res.data.data
    aiStatus.value = data
    qwenEnabled.value = data.qwen_enabled
    yoloEnabled.value = data.yolo_enabled
    ocrEnabled.value = data.ocr_enabled

    const configRes = await axios.get('/api/v1/config')
    const config = configRes.data.data
    qwenConfig.value = { model_path: config.QWEN_MODEL_PATH, quantize: config.QWEN_QUANTIZE, timeout: config.QWEN_INFERENCE_TIMEOUT, base_url: config.QWEN_OLLAMA_BASE_URL }
    yoloConfig.value = { model_path: config.YOLO_MODEL_PATH, conf_threshold: config.YOLO_CONF_THRESHOLD, enabled: config.YOLO_ENABLE }
    ocrConfig.value = { conf_threshold: config.PADDLE_OCR_CONF_THRESHOLD, enabled: config.PADDLE_OCR_ENABLE }
    fallbackEnabled.value = config.FALLBACK_ENABLE
    uiAutomatorEnabled.value = config.UI_AUTOMATOR_ENABLE
    airtestEnabled.value = config.AIRTEST_ENABLE
  } catch (error) { toast.error('刷新失败: ' + error.message) }
}

async function testQwen() {
  try {
    toast.info('正在测试 Qwen-VL 连接...')
    const testImage = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
    const res = await axios.post('/api/v1/ai/analyze', { image_path: testImage, task: '测试连接' })
    showTestModal.value = true
    testResult.value = { title: 'Qwen-VL 测试结果', message: JSON.stringify(res.data, null, 2) }
  } catch (error) {
    showTestModal.value = true
    testResult.value = { title: 'Qwen-VL 测试失败', message: error.message }
  }
}

function startUptimeCounter() {
  let seconds = 0
  uptimeInterval = setInterval(() => {
    seconds++
    const h = String(Math.floor(seconds / 3600)).padStart(2, '0')
    const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0')
    const s = String(seconds % 60).padStart(2, '0')
    uptime.value = `${h}:${m}:${s}`
  }, 1000)
}
</script>

<style scoped>
.flow-node {
  @apply flex flex-col items-center justify-center px-4 py-2.5 rounded-lg border transition-all duration-200 min-w-[80px];
}
.flow-node.active {
  background: #f6ffed;
  border-color: #b7eb8f;
}
.flow-node.inactive {
  background: #fafafa;
  border-color: #f0f0f0;
  opacity: 0.6;
}
.flow-arrow {
  color: #d9d9d9;
  flex-shrink: 0;
}
</style>
