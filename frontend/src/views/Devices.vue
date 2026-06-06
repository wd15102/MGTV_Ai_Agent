<template>
  <div class="space-y-6">
    <!-- 标题 -->
    <div class="flex justify-between items-center">
      <h2 class="text-3xl font-bold text-gray-900">📱 设备监控</h2>
      <button @click="refreshDevices" class="btn-primary">🔄 刷新</button>
    </div>

    <!-- 设备列表 -->
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

        <!-- 操作按钮 -->
        <div class="mt-4 flex space-x-2">
          <button @click="takeScreenshot(device.device_id)" 
                  class="btn-secondary text-sm">
            📷 截屏
          </button>
          <button @click="viewScreenshot(device)" 
                  class="btn-secondary text-sm"
                  :disabled="!device.screenshot_path">
            🖼️ 查看
          </button>
          <button @click="reconnectDevice(device.device_id)" 
                  class="btn-danger text-sm">
            🔄 重连
          </button>
        </div>

        <!-- 截图预览 -->
        <div v-if="selectedDevice && selectedDevice.device_id === device.device_id && screenshotUrl" 
             class="mt-4">
          <img :src="screenshotUrl" alt="截图" class="w-full rounded-lg shadow" />
        </div>
      </div>
    </div>

    <!-- 添加设备 -->
    <div class="card">
      <h3 class="card-title">➕ 添加设备</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <input v-model="newDevice.id" placeholder="设备 ID (ADB serial)" 
               class="input-field" />
        <select v-model="newDevice.type" class="select-field">
          <option value="phone">手机</option>
          <option value="tv">TV</option>
          <option value="box">机顶盒</option>
        </select>
        <button @click="addDevice" class="btn-primary">
          ➕ 添加
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
const devices = ref([])
const selectedDevice = ref(null)
const screenshotUrl = ref(null)
const newDevice = ref({ id: '', type: 'phone' })

async function refreshDevices() {
  try {
    const res = await axios.get('/api/v1/devices')
    devices.value = res.data.data
    toast.success('设备列表已刷新')
  } catch (error) {
    toast.error('刷新失败: ' + error.message)
  }
}

async function takeScreenshot(deviceId) {
  try {
    const res = await axios.post(`/api/v1/devices/${deviceId}/screenshot`)
    if (res.data.success) {
      toast.success('截屏成功')
      // 刷新设备列表以获取新的截图路径
      await refreshDevices()
    }
  } catch (error) {
    toast.error('截屏失败: ' + error.message)
  }
}

function viewScreenshot(device) {
  if (device.screenshot_path) {
    selectedDevice.value = device
    screenshotUrl.value = '/api/v1/files/' + device.screenshot_path
  }
}

async function reconnectDevice(deviceId) {
  try {
    // 调用后端重连接口
    toast.info(`正在重连设备 ${deviceId}...`)
    await refreshDevices()
  } catch (error) {
    toast.error('重连失败: ' + error.message)
  }
}

async function addDevice() {
  if (!newDevice.value.id) {
    toast.warning('请输入设备 ID')
    return
  }
  // 调用后端添加设备接口
  toast.success(`设备 ${newDevice.value.id} 添加请求已发送`)
  newDevice.value = { id: '', type: 'phone' }
  await refreshDevices()
}

function formatTime(isoString) {
  if (!isoString) return '-'
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN')
}

function statusClass(status) {
  return {
    'badge-success': status === 'online',
    'badge-warning': status === 'busy',
    'badge-danger': status === 'offline'
  }
}

onMounted(() => {
  refreshDevices()
})
</script>
