<template>
  <div class="space-y-6">
    <!-- 标题 -->
    <div class="flex justify-between items-center">
      <h2 class="text-3xl font-bold text-gray-900">🧠 AI 状态</h2>
      <button @click="refreshStatus" class="btn-primary">🔄 刷新</button>
    </div>

    <!-- AI Agent 状态 -->
    <div class="card">
      <h3 class="card-title">🤖 AI Agent 决策大脑</h3>
      <div v-if="aiStatus" class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="stat-box">
          <p class="stat-label">状态</p>
          <p :class="aiStatus.status === 'ready' ? 'text-green-600' : 'text-red-600'" 
             class="stat-value">
            {{ aiStatus.status }}
          </p>
        </div>
        <div class="stat-box">
          <p class="stat-label">当前任务</p>
          <p class="stat-value text-sm">{{ aiStatus.current_task || '-' }}</p>
        </div>
        <div class="stat-box">
          <p class="stat-label">思考历史</p>
          <p class="stat-value">{{ aiStatus.thought_history_len || 0 }} 条</p>
        </div>
        <div class="stat-box">
          <p class="stat-label">运行时间</p>
          <p class="stat-value text-sm">{{ uptime }}</p>
        </div>
      </div>
      <div v-else class="text-center py-4 text-gray-500">
        加载中...
      </div>
    </div>

    <!-- 模型状态 -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <!-- Qwen-VL -->
      <div class="card">
        <div class="flex items-center justify-between mb-4">
          <h4 class="text-lg font-semibold">🌐 Qwen-VL-7B</h4>
          <span :class="qwenEnabled ? 'badge-success' : 'badge-danger'" class="badge">
            {{ qwenEnabled ? '✅ 已启用' : '❌ 未启用' }}
          </span>
        </div>
        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-gray-600">模型路径</span>
            <span class="font-mono text-xs">{{ qwenConfig.model_path }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600">量化方式</span>
            <span class="font-mono">{{ qwenConfig.quantize }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600">推理超时</span>
            <span>{{ qwenConfig.timeout }} 秒</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600">API 地址</span>
            <span class="font-mono text-xs">{{ qwenConfig.base_url }}</span>
          </div>
        </div>
        <button @click="testQwen" class="mt-4 btn-secondary w-full text-sm">
          🧪 测试连接
        </button>
      </div>

      <!-- YOLOv8 -->
      <div class="card">
        <div class="flex items-center justify-between mb-4">
          <h4 class="text-lg font-semibold">🎯 YOLOv8</h4>
          <span :class="yoloEnabled ? 'badge-success' : 'badge-danger'" class="badge">
            {{ yoloEnabled ? '✅ 已启用' : '❌ 未启用' }}
          </span>
        </div>
        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-gray-600">模型路径</span>
            <span class="font-mono text-xs">{{ yoloConfig.model_path }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600">置信度阈值</span>
            <span>{{ yoloConfig.conf_threshold }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600">启用状态</span>
            <span>{{ yoloConfig.enabled ? '是' : '否' }}</span>
          </div>
        </div>
        <button @click="testYolo" class="mt-4 btn-secondary w-full text-sm">
          🧪 测试检测
        </button>
      </div>

      <!-- PaddleOCR -->
      <div class="card">
        <div class="flex items-center justify-between mb-4">
          <h4 class="text-lg font-semibold">📝 PaddleOCR</h4>
          <span :class="ocrEnabled ? 'badge-success' : 'badge-danger'" class="badge">
            {{ ocrEnabled ? '✅ 已启用' : '❌ 未启用' }}
          </span>
        </div>
        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-gray-600">置信度阈值</span>
            <span>{{ ocrConfig.conf_threshold }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600">启用状态</span>
            <span>{{ ocrConfig.enabled ? '是' : '否' }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600">语言</span>
            <span>中文</span>
          </div>
        </div>
        <button @click="testOcr" class="mt-4 btn-secondary w-full text-sm">
          🧪 测试识别
        </button>
      </div>
    </div>

    <!-- 降级策略 -->
    <div class="card">
      <h3 class="card-title">🔄 降级策略</h3>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="stat-box">
          <p class="stat-label">降级启用</p>
          <p :class="fallbackEnabled ? 'text-green-600' : 'text-gray-400'" 
             class="stat-value">
            {{ fallbackEnabled ? '✅' : '❌' }}
          </p>
        </div>
        <div class="stat-box">
          <p class="stat-label">uiautomator2</p>
          <p :class="uiAutomatorEnabled ? 'text-green-600' : 'text-gray-400'" 
             class="stat-value">
            {{ uiAutomatorEnabled ? '✅' : '❌' }}
          </p>
        </div>
        <div class="stat-box">
          <p class="stat-label">Airtest</p>
          <p :class="airtestEnabled ? 'text-green-600' : 'text-gray-400'" 
             class="stat-value">
            {{ airtestEnabled ? '✅' : '❌' }}
          </p>
        </div>
        <div class="stat-box">
          <p class="stat-label">策略说明</p>
          <p class="stat-value text-xs">Qwen→uiautomator→Airtest</p>
        </div>
      </div>
    </div>

    <!-- 测试弹窗 -->
    <div v-if="showTestModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-xl p-6 w-full max-w-2xl">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-xl font-bold">{{ testResult.title }}</h3>
          <button @click="showTestModal = false" class="text-gray-500 hover:text-gray-700">
            ✕
          </button>
        </div>
        <div class="bg-gray-100 p-4 rounded-lg">
          <pre class="text-sm whitespace-pre-wrap">{{ testResult.message }}</pre>
        </div>
        <button @click="showTestModal = false" class="mt-4 btn-primary w-full">
          关闭
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
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
const uptime = ref('-')
const showTestModal = ref(false)
const testResult = ref({ title: '', message: '' })

// 配置（从后端获取）
const qwenConfig = ref({
  model_path: './models/qwen-vl-7b',
  quantize: 'INT4',
  timeout: 5,
  base_url: 'http://localhost:11434'
})

const yoloConfig = ref({
  model_path: './models/yolov8/best.pt',
  conf_threshold: 0.85,
  enabled: true
})

const ocrConfig = ref({
  conf_threshold: 0.5,
  enabled: true
})

onMounted(async () => {
  await refreshStatus()
  startUptimeCounter()
})

async function refreshStatus() {
  try {
    const res = await axios.get('/api/v1/ai/status')
    const data = res.data.data
    
    aiStatus.value = data
    qwenEnabled.value = data.qwen_enabled
    yoloEnabled.value = data.yolo_enabled
    ocrEnabled.value = data.ocr_enabled
    
    // 获取配置
    const configRes = await axios.get('/api/v1/config')
    const config = configRes.data.data
    
    qwenConfig.value = {
      model_path: config.QWEN_MODEL_PATH,
      quantize: config.QWEN_QUANTIZE,
      timeout: config.QWEN_INFERENCE_TIMEOUT,
      base_url: config.QWEN_OLLAMA_BASE_URL
    }
    
    yoloConfig.value = {
      model_path: config.YOLO_MODEL_PATH,
      conf_threshold: config.YOLO_CONF_THRESHOLD,
      enabled: config.YOLO_ENABLE
    }
    
    ocrConfig.value = {
      conf_threshold: config.PADDLE_OCR_CONF_THRESHOLD,
      enabled: config.PADDLE_OCR_ENABLE
    }
    
    fallbackEnabled.value = config.FALLBACK_ENABLE
    uiAutomatorEnabled.value = config.UI_AUTOMATOR_ENABLE
    airtestEnabled.value = config.AIRTEST_ENABLE
    
    toast.success('AI 状态已刷新')
  } catch (error) {
    toast.error('刷新失败: ' + error.message)
  }
}

async function testQwen() {
  try {
    toast.info('正在测试 Qwen-VL 连接...')
    
    // 创建一个测试图片（1x1像素）
    const testImage = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
    
    const res = await axios.post('/api/v1/ai/analyze', {
      image_path: testImage,
      task: '测试连接'
    })
    
    showTestModal.value = true
    testResult.value = {
      title: 'Qwen-VL 测试结果',
      message: JSON.stringify(res.data, null, 2)
    }
  } catch (error) {
    showTestModal.value = true
    testResult.value = {
      title: 'Qwen-VL 测试失败',
      message: error.message
    }
  }
}

async function testYolo() {
  toast.info('YOLOv8 测试功能开发中...')
}

async function testOcr() {
  toast.info('PaddleOCR 测试功能开发中...')
}

function startUptimeCounter() {
  // 简单的运行时间计数器
  let seconds = 0
  setInterval(() => {
    seconds++
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    uptime.value = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }, 1000)
}
</script>
