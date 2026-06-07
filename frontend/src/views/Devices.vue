<template>
  <div class="device-monitor">
    <!-- 空状态 -->
    <div v-if="devices.length === 0" class="device-empty">
      <div class="empty-graphic">
        <svg viewBox="0 0 120 120" fill="none">
          <circle cx="60" cy="60" r="55" stroke="currentColor" stroke-width="0.8" opacity="0.12"/>
          <circle cx="60" cy="60" r="42" stroke="currentColor" stroke-width="0.5" opacity="0.08"/>
          <rect x="35" y="32" width="50" height="38" rx="3" stroke="currentColor" stroke-width="1.2" opacity="0.25"/>
          <circle cx="60" cy="51" r="5" stroke="currentColor" stroke-width="0.8" opacity="0.2"/>
          <path d="M40 65 l40 0" stroke="currentColor" stroke-width="0.8" opacity="0.15"/>
          <rect x="44" y="72" width="32" height="20" rx="3" stroke="currentColor" stroke-width="1" opacity="0.2"/>
          <circle cx="60" cy="82" r="6" stroke="currentColor" stroke-width="0.8" opacity="0.15"/>
        </svg>
      </div>
      <p class="empty-main">暂无设备连接</p>
      <p class="empty-sub">通过 ADB 连接设备后自动显示</p>
    </div>

    <!-- 设备列表 -->
    <div class="device-grid" v-if="devices.length > 0">
      <div v-for="device in devices" :key="device.device_id" class="device-card"
           :class="{ 'card-offline': device.status !== 'online' }">

        <!-- 卡片头部 -->
        <div class="card-hd">
          <div class="card-hd-left">
            <div class="dot-ring" :class="'dot-ring-' + device.status">
              <span class="dot-inner"></span>
            </div>
            <div class="device-info">
              <div class="device-name-row">
                <span class="device-name">{{ device.name || device.device_id }}</span>
              </div>
              <div class="device-badges">
                <span class="badge" :class="'badge-' + device.status">
                  {{ { online: 'ONLINE', busy: 'BUSY', offline: 'OFFLINE' }[device.status] || device.status }}
                </span>
                <span class="badge badge-type">{{ device.type || 'UNKNOWN' }}</span>
                <span v-if="liveMap[device.device_id]" class="badge badge-live">LIVE</span>
              </div>
            </div>
          </div>
          <div class="card-hd-right">
            <span class="os-tag">Android {{ device.android_version || '?' }}</span>
          </div>
        </div>

        <!-- 卡片主体 -->
        <div class="card-bd">

          <!-- ====== 左列: 屏幕画面 ====== -->
          <div class="screen-col">
            <div class="screen-frame">
              <!-- 暗色屏幕区域 -->
              <div class="screen-viewport" ref="screenRefs" :data-device="device.device_id"
                   @click="handleScreenClick(device, $event)">

                <!-- Canvas 实时画面（LIVE 模式） -->
                <canvas v-show="liveMap[device.device_id]"
                        :ref="el => setCanvasRef(device.device_id, el)"
                        class="screen-canvas"
                        :width="canvasWidth"
                        :height="canvasHeight">
                </canvas>

                <!-- 静态截图（非 LIVE 模式） -->
                <img v-show="!liveMap[device.device_id] && screenshotUrls[device.device_id]"
                     :src="screenshotUrls[device.device_id]"
                     class="screen-img"
                     @error="screenshotErrors[device.device_id]=true"
                     draggable="false" />

                <!-- 连接中（LIVE 启动时） -->
                <div v-if="connectingMap[device.device_id] && !fpsInfo[device.device_id]"
                     class="screen-overlay">
                  <div class="spinner-sm"></div>
                  <span class="overlay-text">CONNECTING</span>
                </div>

                <!-- 加载状态 -->
                <div v-if="loadingScreenshots[device.device_id] && !liveMap[device.device_id]"
                     class="screen-overlay">
                  <div class="spinner-sm"></div>
                  <span class="overlay-text">CAPTURING</span>
                </div>

                <!-- 出错状态 -->
                <div v-if="screenshotErrors[device.device_id] && !liveMap[device.device_id]"
                     class="screen-overlay screen-error">
                  <svg class="overlay-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                  </svg>
                  <span class="overlay-text">NO SIGNAL</span>
                </div>

                <!-- LIVE 水印 -->
                <div v-if="liveMap[device.device_id]" class="live-badge">
                  <span class="live-dot"></span>
                  <span>LIVE</span>
                </div>

                <!-- 帧率信息 -->
                <div v-if="liveMap[device.device_id] && fpsInfo[device.device_id]" class="fps-badge">
                  {{ fpsInfo[device.device_id] }} fps
                </div>

                <!-- 点击模式提示 -->
                <div v-if="clickModeMap[device.device_id]" class="click-hint">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="12" height="12">
                    <path d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5"/>
                  </svg>
                  点击画面模拟触控
                </div>
              </div>

              <!-- 底部状态条 -->
              <div class="screen-bar">
                <div class="bar-left">
                  <span class="bar-chip">{{ device.resolution || '--x--' }}</span>
                </div>
                <div class="bar-right">
                  <span v-if="screenshotTimestamps[device.device_id] && !liveMap[device.device_id]" class="bar-chip">
                    {{ formatTimeAgo(screenshotTimestamps[device.device_id]) }}
                  </span>
                </div>
              </div>
            </div>

            <!-- 工具栏 -->
            <div class="screen-tools">
              <button @click="takeScreenshot(device.device_id)" class="tool-icon" title="截图"
                      :disabled="loadingScreenshots[device.device_id]">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2v11z"/>
                  <circle cx="12" cy="13" r="4"/>
                </svg>
              </button>

              <button @click="toggleLive(device.device_id)" class="tool-icon"
                      :class="{ 'tool-active': liveMap[device.device_id] }" title="实时画面">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
              </button>

              <div class="tool-divider"></div>

              <button @click="previewScreenshot(device.device_id)"
                      v-if="screenshotUrls[device.device_id] && !liveMap[device.device_id]"
                      class="tool-icon" title="放大">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                  <line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/>
                </svg>
              </button>

              <label class="tool-icon toggle-label" :class="{ 'tool-active': clickModeMap[device.device_id] }">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5"/>
                </svg>
                <input type="checkbox" v-model="clickModeMap[device.device_id]" class="hidden" />
              </label>
            </div>
          </div>

          <!-- ====== 右列: 遥控器 + 信息 ====== -->
          <div class="ctrl-col">

            <!-- 遥控器 -->
            <div class="ctrl-section">
              <div class="ctrl-label">REMOTE</div>
              <div class="ctrl-layout">
                <!-- D-Pad -->
                <div class="dpad">
                  <button @click="sendKey(device.device_id, 'UP')" class="btn-dp" title="上">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 5l-7 7h14l-7-7z"/></svg>
                  </button>
                  <div class="dp-mid">
                    <button @click="sendKey(device.device_id, 'LEFT')" class="btn-dp" title="左">
                      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M5 12l7-7v14l-7-7z"/></svg>
                    </button>
                    <button @click="sendKey(device.device_id, 'OK')" class="btn-ok">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                        <polyline points="20 6 9 17 4 12"/>
                      </svg>
                    </button>
                    <button @click="sendKey(device.device_id, 'RIGHT')" class="btn-dp" title="右">
                      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M19 12l-7-7v14l7-7z"/></svg>
                    </button>
                  </div>
                  <button @click="sendKey(device.device_id, 'DOWN')" class="btn-dp" title="下">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 19l7-7H5l7 7z"/></svg>
                  </button>
                </div>

                <!-- 动作键 -->
                <div class="act-keys">
                  <button @click="sendKey(device.device_id, 'HOME')" class="btn-act">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                      <path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
                    </svg>
                    <span>HOME</span>
                  </button>
                  <button @click="sendKey(device.device_id, 'BACK')" class="btn-act">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                      <path d="M19 12H5m7-7l-7 7 7 7"/>
                    </svg>
                    <span>BACK</span>
                  </button>
                  <button @click="sendKey(device.device_id, 'MENU')" class="btn-act">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                      <circle cx="12" cy="5" r="1.5" fill="currentColor"/>
                      <circle cx="12" cy="12" r="1.5" fill="currentColor"/>
                      <circle cx="12" cy="19" r="1.5" fill="currentColor"/>
                    </svg>
                    <span>MENU</span>
                  </button>
                </div>
              </div>

              <!-- 功能键 -->
              <div class="fn-bar">
                <button @click="sendKey(device.device_id, 'VOLUME_UP')" class="btn-fn" title="音量+">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                    <path d="M19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07"/>
                  </svg>
                </button>
                <button @click="sendKey(device.device_id, 'VOLUME_DOWN')" class="btn-fn" title="音量-">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                    <path d="M15.54 8.46a5 5 0 010 7.07"/>
                  </svg>
                </button>
                <button @click="sendKey(device.device_id, 'MUTE')" class="btn-fn" title="静音">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                    <line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/>
                  </svg>
                </button>
                <button @click="sendKey(device.device_id, 'MEDIA_PLAY_PAUSE')" class="btn-fn" title="播放/暂停">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                    <polygon points="5 3 19 12 5 21 5 3"/>
                  </svg>
                </button>
                <button @click="sendKey(device.device_id, 'POWER')" class="btn-fn btn-fn-red" title="电源">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                    <path d="M18.36 6.64a9 9 0 11-12.73 0M12 2v10"/>
                  </svg>
                </button>
              </div>
            </div>

            <!-- 设备信息 -->
            <div class="ctrl-section info-sect">
              <div class="ctrl-label">DEVICE INFO</div>
              <div class="info-grid">
                <div class="info-cell">
                  <span class="info-key">TYPE</span>
                  <span class="info-val">{{ device.type || '-' }}</span>
                </div>
                <div class="info-cell">
                  <span class="info-key">ANDROID</span>
                  <span class="info-val">{{ device.android_version || '-' }}</span>
                </div>
                <div class="info-cell">
                  <span class="info-key">SDK</span>
                  <span class="info-val mono">{{ device.sdk_version || '-' }}</span>
                </div>
                <div class="info-cell">
                  <span class="info-key">RES</span>
                  <span class="info-val mono">{{ device.resolution || '-' }}</span>
                </div>
                <div class="info-cell">
                  <span class="info-key">HEARTBEAT</span>
                  <span class="info-val mono">{{ formatTime(device.last_heartbeat) }}</span>
                </div>
                <div class="info-cell">
                  <span class="info-key">CID</span>
                  <span class="info-val mono truncate">{{ device.device_id?.split(':')[0] || '-' }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 卡片底部 -->
        <div class="card-ft">
          <div class="ft-left">
            <div class="ft-dot" :class="'ft-dot-' + device.status"></div>
            <span class="ft-id">{{ device.device_id }}</span>
          </div>
          <div class="ft-right">
            <span class="ft-time">{{ formatTime(device.last_heartbeat) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 全屏预览 Modal -->
    <Teleport to="body">
      <div v-if="previewModal" class="modal-mask" @click.self="previewModal=null">
        <div class="modal-box">
          <div class="modal-corners"></div>
          <button @click="previewModal=null" class="modal-x">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
          <div class="modal-title">SCREEN PREVIEW</div>
          <img :src="screenshotUrls[previewModal]" alt="preview" class="modal-img" />
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import axios from 'axios'

// ========= State =========
const devices = ref([])
const screenshotUrls = reactive({})
const screenshotTimestamps = reactive({})
const screenshotErrors = reactive({})
const loadingScreenshots = reactive({})
const previewModal = ref(null)
const clickModeMap = reactive({})
const liveMap = reactive({})          // 是否开启实时画面
const connectingMap = reactive({})    // WebSocket 连接中
const fpsInfo = reactive({})          // 当前帧率
const canvasWidth = ref(320)
const canvasHeight = ref(640)
const refreshing = ref(false)

// ========= WebSocket 管理 =========
const wsMap = {}         // device_id -> WebSocket
const canvasRefMap = {}  // device_id -> canvas element
const animationIdMap = {} // device_id -> requestAnimationFrame id
const frameQueueMap = {}  // device_id -> [ImageBitmap]
const wsReconnectTimer = {}

function setCanvasRef(deviceId, el) {
  if (el) canvasRefMap[deviceId] = el
}

function connectLiveStream(deviceId) {
  if (wsMap[deviceId]) return  // already connected

  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = location.host
  const ws = new WebSocket(`${protocol}//${host}/ws/device/${deviceId}/screen`)

  ws.binaryType = 'arraybuffer'

  ws.onopen = () => {
    console.log(`[LIVE] ${deviceId} WebSocket connected`)
    fpsInfo[deviceId] = 0
    frameQueueMap[deviceId] = []
    connectingMap[deviceId] = false
    startCanvasRender(deviceId)
  }

  ws.onmessage = async (event) => {
    if (event.data instanceof ArrayBuffer) {
      try {
        const blob = new Blob([event.data], { type: 'image/jpeg' })
        const bitmap = await createImageBitmap(blob)
        if (frameQueueMap[deviceId]) {
          // Only keep latest frame in queue (drop old ones)
          frameQueueMap[deviceId][0] = bitmap
        }
      } catch (e) {
        // skip decode errors for corrupted frames
      }
    } else if (typeof event.data === 'string') {
      try {
        const info = JSON.parse(event.data)
        if (info.type === 'stream_info') {
          console.log(`[LIVE] ${deviceId} stream: ${info.width}x${info.height} ${info.codec}`)
          // Pre-size canvas
          const canvas = canvasRefMap[deviceId]
          if (canvas && info.width && info.height) {
            canvas.width = info.width
            canvas.height = info.height
            canvasWidth.value = info.width
            canvasHeight.value = info.height
          }
        }
      } catch (e) {
        // not JSON, check for ping/pong
        if (event.data === 'ping') ws.send('pong')
      }
    }
  }

  ws.onclose = () => {
    console.log(`[LIVE] ${deviceId} WebSocket disconnected`)
    stopCanvasRender(deviceId)
    delete wsMap[deviceId]
    // Auto reconnect after 2s
    if (liveMap[deviceId]) {
      wsReconnectTimer[deviceId] = setTimeout(() => connectLiveStream(deviceId), 2000)
    }
  }

  ws.onerror = () => {
    ws.close()
  }

  wsMap[deviceId] = ws
}

function disconnectLiveStream(deviceId) {
  if (wsReconnectTimer[deviceId]) {
    clearTimeout(wsReconnectTimer[deviceId])
    delete wsReconnectTimer[deviceId]
  }
  stopCanvasRender(deviceId)
  if (wsMap[deviceId]) {
    wsMap[deviceId].close()
    delete wsMap[deviceId]
  }
  if (frameQueueMap[deviceId]) {
    frameQueueMap[deviceId].forEach(b => b.close())
    delete frameQueueMap[deviceId]
  }
  fpsInfo[deviceId] = 0
}

function startCanvasRender(deviceId) {
  const canvas = canvasRefMap[deviceId]
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  let frameCount = 0
  let lastFpsTime = performance.now()

  function renderFrame(timestamp) {
    if (!frameQueueMap[deviceId] || !frameQueueMap[deviceId][0]) {
      animationIdMap[deviceId] = requestAnimationFrame(renderFrame)
      return
    }

    // Calculate FPS
    frameCount++
    const elapsed = timestamp - lastFpsTime
    if (elapsed >= 1000) {
      fpsInfo[deviceId] = Math.round(frameCount * 1000 / elapsed)
      frameCount = 0
      lastFpsTime = timestamp
    }

    // Dequeue latest frame
    const bitmap = frameQueueMap[deviceId].shift()
    if (bitmap) {
      // Adjust canvas size to match frame
      if (canvas.width !== bitmap.width || canvas.height !== bitmap.height) {
        canvas.width = bitmap.width
        canvas.height = bitmap.height
        canvasWidth.value = bitmap.width
        canvasHeight.value = bitmap.height
      }
      ctx.drawImage(bitmap, 0, 0)
      bitmap.close()  // free memory
    }

    animationIdMap[deviceId] = requestAnimationFrame(renderFrame)
  }

  animationIdMap[deviceId] = requestAnimationFrame(renderFrame)
}

function stopCanvasRender(deviceId) {
  if (animationIdMap[deviceId]) {
    cancelAnimationFrame(animationIdMap[deviceId])
    delete animationIdMap[deviceId]
  }
  // Clear queue
  if (frameQueueMap[deviceId]) {
    frameQueueMap[deviceId].forEach(b => {
      try { b.close() } catch(e) {}
    })
    frameQueueMap[deviceId] = []
  }
}

function toggleLive(deviceId) {
  liveMap[deviceId] = !liveMap[deviceId]
  if (liveMap[deviceId]) {
    connectingMap[deviceId] = true
    fpsInfo[deviceId] = 0
    connectLiveStream(deviceId)
  } else {
    disconnectLiveStream(deviceId)
    connectingMap[deviceId] = false
    // Fall back to static screenshot
    takeScreenshot(deviceId)
  }
}

// ========= Device Management =========
const onlineCount = computed(() => devices.value.filter(d => d.status === 'online').length)

async function refreshDevices() {
  refreshing.value = true
  try {
    const res = await axios.get('/api/v1/devices')
    devices.value = res.data.data || []
    // Auto-screenshot for new online devices
    for (const d of devices.value) {
      if (d.status === 'online' && !screenshotUrls[d.device_id] && !liveMap[d.device_id]) {
        await takeScreenshot(d.device_id)
      }
    }
  } catch (e) {
    console.error('[DEVICE] refresh error:', e)
  } finally {
    refreshing.value = false
  }
}

async function takeScreenshot(deviceId) {
  if (!deviceId || liveMap[deviceId]) return
  loadingScreenshots[deviceId] = true
  screenshotErrors[deviceId] = false
  try {
    const res = await axios.post(`/api/v1/devices/${deviceId}/screenshot/stream`)
    if (res.data.success && res.data.base64) {
      screenshotUrls[deviceId] = res.data.base64
      screenshotTimestamps[deviceId] = Date.now()
    } else {
      screenshotErrors[deviceId] = true
    }
  } catch {
    screenshotErrors[deviceId] = true
  } finally {
    loadingScreenshots[deviceId] = false
  }
}

async function handleScreenClick(device, event) {
  if (!clickModeMap[device.device_id]) return
  const rect = event.currentTarget.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  const img = event.currentTarget.querySelector('img') || event.currentTarget.querySelector('canvas')
  if (img) {
    const scaleX = (img.naturalWidth || img.width) / rect.width
    const scaleY = (img.naturalHeight || img.height) / rect.height
    await axios.post(`/api/v1/devices/${device.device_id}/click`, null, {
      params: { x: Math.round(x * scaleX), y: Math.round(y * scaleY) }
    }).catch(() => {})
  }
}

async function sendKey(deviceId, keycode) {
  try {
    await axios.post(`/api/v1/devices/${deviceId}/keyevent`, { keycode })
  } catch {}
}

function previewScreenshot(id) {
  if (screenshotUrls[id]) previewModal.value = id
}

// ========= Formatters =========
function formatTime(iso) {
  return iso ? new Date(iso).toLocaleTimeString('zh-CN', { hour12: false }) : '-'
}
function formatTimeAgo(ts) {
  if (!ts) return ''
  const d = Date.now() - ts
  if (d < 1000) return 'now'
  if (d < 60000) return `${Math.floor(d/1000)}s`
  return `${Math.floor(d/60000)}m`
}

// ========= Lifecycle =========
onMounted(refreshDevices)
onUnmounted(() => {
  // Clean up all live streams
  Object.keys(liveMap).forEach(k => {
    if (liveMap[k]) disconnectLiveStream(k)
  })
})
</script>

<style scoped>
/* ============================================================
   DEVICE MONITOR — 卡片式科技风布局
   ============================================================ */
.device-monitor {
  padding: 0;
}

/* ---------- 空状态 ---------- */
.device-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-height: 400px; color: #bfbfbf;
}
.empty-graphic { width: 100px; height: 100px; margin-bottom: 18px; }
.empty-main { font-size: 14px; font-weight: 600; color: #8c8c8c; margin-bottom: 4px; }
.empty-sub { font-size: 12px; }

/* ---------- 设备网格 ---------- */
.device-grid { display: grid; gap: 18px; }

/* ============================================================
   设备卡片
   ============================================================ */
.device-card {
  background: #fff;
  border-radius: 10px;
  border: 1px solid #e8e8e8;
  overflow: hidden;
  transition: all 0.25s cubic-bezier(.4,0,.2,1);
}
.device-card:hover {
  border-color: #d6e4ff;
  box-shadow: 0 6px 20px rgba(22,119,255,0.07);
}
.card-offline { opacity: 0.6; }

/* -- 头部 -- */
.card-hd {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  background: linear-gradient(135deg, #fafbfc 0%, #fff 100%);
}
.card-hd-left { display: flex; align-items: center; gap: 10px; }

/* 状态指示灯 - 呼吸环 */
.dot-ring {
  position: relative; width: 12px; height: 12px;
  display: flex; align-items: center; justify-content: center;
}
.dot-ring::before {
  content: ''; position: absolute; inset: -4px;
  border-radius: 50%; opacity: 0;
}
.dot-ring-online::before {
  background: rgba(82,196,26,0.3);
  animation: breathe 2s infinite;
}
.dot-ring-busy::before {
  background: rgba(250,173,20,0.4);
  animation: breathe 1s infinite;
}
@keyframes breathe {
  0% { transform: scale(0.6); opacity: 0.5; }
  50% { transform: scale(1.8); opacity: 0; }
  100% { transform: scale(0.6); opacity: 0.5; }
}
.dot-inner {
  width: 8px; height: 8px; border-radius: 50%; position: relative; z-index: 1;
}
.dot-ring-online .dot-inner { background: #52c41a; box-shadow: 0 0 8px rgba(82,196,26,.5); }
.dot-ring-busy .dot-inner { background: #faad14; }
.dot-ring-offline .dot-inner { background: #d9d9d9; }

.device-info { display: flex; flex-direction: column; gap: 2px; }
.device-name-row { display: flex; align-items: center; gap: 8px; }
.device-name { font-size: 14px; font-weight: 700; color: #1f1f1f; }
.device-badges { display: flex; gap: 4px; flex-wrap: wrap; }

.badge {
  font-size: 9px; font-weight: 700; letter-spacing: .08em;
  padding: 1px 6px; border-radius: 3px;
}
.badge-online { color: #52c41a; background: rgba(82,196,26,.1); }
.badge-busy { color: #faad14; background: rgba(250,173,20,.1); }
.badge-offline { color: #8c8c8c; background: #f5f5f5; }
.badge-type { color: #1677ff; background: rgba(22,119,255,.08); }
.badge-live { color: #ff4d4f; background: rgba(255,77,79,.1); animation: blink 1.2s infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }

.os-tag { font-size: 11px; color: #8c8c8c; font-family: 'SF Mono','Fira Code',monospace; }

/* -- 主体双列 -- */
.card-bd { display: flex; min-height: 300px; }

/* ============================================================
   左列: 屏幕画面
   ============================================================ */
.screen-col {
  width: 280px; flex-shrink: 0;
  display: flex; flex-direction: column;
  border-right: 1px solid #f0f0f0;
}

.screen-frame {
  position: relative; flex: 1;
  display: flex; flex-direction: column;
  background: #0d1117;
  min-height: 200px; overflow: hidden;
}
.screen-viewport {
  flex: 1;
  display: flex; align-items: center; justify-content: center;
  position: relative; cursor: crosshair;
}
.screen-img {
  width: 100%; height: 100%; object-fit: contain;
  max-height: 280px;
}
.screen-canvas {
  width: 100%; height: 100%; object-fit: contain;
  display: block;
}

/* 覆盖状态 */
.screen-overlay {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 8px; color: rgba(255,255,255,.25);
}
.overlay-text { font-size: 9px; letter-spacing: .15em; font-weight: 600; }
.spinner-sm {
  width: 24px; height: 24px;
  border: 2px solid rgba(255,255,255,.06);
  border-top-color: #1677ff;
  border-radius: 50%; animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.screen-error .overlay-icon { width: 24px; height: 24px; color: #ff4d4f; }
.screen-error .overlay-text { color: rgba(255,77,79,.5); }

/* LIVE 水印 */
.live-badge {
  position: absolute; top: 8px; left: 8px;
  display: flex; align-items: center; gap: 4px;
  padding: 2px 8px;
  background: rgba(255,77,79,.85);
  color: #fff; font-size: 9px; font-weight: 700;
  letter-spacing: .1em; border-radius: 3px;
  z-index: 10;
}
.live-dot {
  width: 5px; height: 5px; border-radius: 50%;
  background: #fff; animation: blink 1s infinite;
}

/* FPS 显示 */
.fps-badge {
  position: absolute; top: 8px; right: 8px;
  padding: 2px 7px;
  background: rgba(0,0,0,.55);
  color: rgba(255,255,255,.7); font-size: 9px;
  font-family: 'SF Mono','Fira Code',monospace;
  border-radius: 3px; z-index: 10;
}

/* 点击模式提示 */
.click-hint {
  position: absolute; bottom: 32px; left: 50%;
  transform: translateX(-50%);
  display: flex; align-items: center; gap: 4px;
  padding: 3px 10px;
  background: rgba(22,119,255,.85);
  color: #fff; font-size: 9px; font-weight: 600;
  border-radius: 4px; white-space: nowrap; z-index: 10;
  animation: fadeInUp .3s ease;
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateX(-50%) translateY(6px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

/* 底部信息条 */
.screen-bar {
  position: absolute; bottom: 0; left: 0; right: 0;
  display: flex; align-items: center; justify-content: space-between;
  padding: 5px 8px; z-index: 5;
  background: linear-gradient(transparent, rgba(0,0,0,.7));
}
.bar-chip {
  font-size: 9px; font-family: 'SF Mono','Fira Code',monospace;
  color: rgba(255,255,255,.4);
  background: rgba(0,0,0,.25);
  padding: 1px 5px; border-radius: 3px;
}

/* -- 工具栏 -- */
.screen-tools {
  display: flex; align-items: center; gap: 1px;
  padding: 5px 8px;
  background: #fafafa; border-top: 1px solid #f0f0f0;
}
.tool-icon {
  width: 28px; height: 24px;
  display: flex; align-items: center; justify-content: center;
  border: none; background: transparent;
  color: #8c8c8c; cursor: pointer;
  border-radius: 4px; transition: all .12s;
}
.tool-icon svg { width: 13px; height: 13px; }
.tool-icon:hover { color: #1677ff; background: rgba(22,119,255,.06); }
.tool-icon:disabled { opacity: .3; cursor: not-allowed; }
.tool-active { color: #1677ff; background: rgba(22,119,255,.1); }
.tool-divider { width: 1px; height: 14px; background: #e8e8e8; margin: 0 4px; }
.toggle-label input { display: none; }

/* ============================================================
   右列: 遥控器
   ============================================================ */
.ctrl-col { flex: 1; display: flex; flex-direction: column; min-width: 0; }

.ctrl-section { padding: 12px 14px; }
.ctrl-section + .ctrl-section { border-top: 1px solid #f5f5f5; }

.ctrl-label {
  font-size: 8px; font-weight: 700; letter-spacing: .15em;
  color: #bfbfbf; margin-bottom: 8px;
}

/* D-Pad + 动作键并排 */
.ctrl-layout { display: flex; gap: 14px; align-items: flex-start; }

/* D-Pad */
.dpad { display: flex; flex-direction: column; align-items: center; gap: 2px; flex-shrink: 0; }
.dp-mid { display: flex; align-items: center; gap: 2px; }

.btn-dp {
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid #e0e0e0; border-radius: 7px;
  background: #f8f9fa; color: #666;
  cursor: pointer; transition: all .1s;
}
.btn-dp svg { width: 13px; height: 13px; fill: currentColor; }
.btn-dp:hover {
  background: #1677ff; color: #fff; border-color: #1677ff;
  box-shadow: 0 2px 6px rgba(22,119,255,.25);
  transform: translateY(-1px);
}
.btn-dp:active { transform: scale(.92); }

.btn-ok {
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  border: none; border-radius: 50%;
  background: linear-gradient(135deg, #1677ff, #4096ff);
  color: #fff; cursor: pointer; transition: all .12s;
  box-shadow: 0 2px 6px rgba(22,119,255,.3);
}
.btn-ok svg { width: 15px; height: 15px; }
.btn-ok:hover {
  box-shadow: 0 4px 12px rgba(22,119,255,.4);
  transform: translateY(-1px);
}
.btn-ok:active { transform: scale(.9); }

/* 动作键 */
.act-keys { display: flex; flex-direction: column; gap: 3px; }
.btn-act {
  display: flex; align-items: center; gap: 5px;
  padding: 4px 9px;
  border: 1px solid #e8e8e8; border-radius: 5px;
  background: #fafafa; color: #555;
  font-size: 9px; font-weight: 600; letter-spacing: .08em;
  cursor: pointer; transition: all .12s;
}
.btn-act svg { width: 11px; height: 11px; flex-shrink: 0; }
.btn-act:hover {
  background: #fff; color: #1677ff;
  border-color: #d6e4ff;
  box-shadow: 0 1px 3px rgba(22,119,255,.08);
}
.btn-act:active { transform: scale(.97); }

/* 功能键行 */
.fn-bar { display: flex; gap: 3px; margin-top: 10px; }
.btn-fn {
  width: 32px; height: 26px;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid #e8e8e8; border-radius: 4px;
  background: #fafafa; color: #8c8c8c;
  cursor: pointer; transition: all .1s;
}
.btn-fn svg { width: 12px; height: 12px; }
.btn-fn:hover { background: #fff; color: #595959; border-color: #d9d9d9; }
.btn-fn:active { transform: scale(.93); }
.btn-fn-red:hover { color: #ff4d4f; border-color: #ffccc7; background: #fff2f0; }

/* -- 设备信息 -- */
.info-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 5px;
}
.info-cell {
  background: #fafafa; border-radius: 5px;
  padding: 7px 9px; border: 1px solid #f0f0f0;
}
.info-key {
  display: block; font-size: 7px; font-weight: 700;
  letter-spacing: .1em; color: #bfbfbf; margin-bottom: 1px;
}
.info-val {
  display: block; font-size: 11px; font-weight: 600; color: #1f1f1f;
}
.info-val.mono { font-family: 'SF Mono','Fira Code',monospace; font-size: 10px; }

/* -- 卡片底部 -- */
.card-ft {
  display: flex; align-items: center; justify-content: space-between;
  padding: 5px 14px;
  background: #fafafa; border-top: 1px solid #f0f0f0;
}
.ft-left { display: flex; align-items: center; gap: 5px; }
.ft-dot { width: 4px; height: 4px; border-radius: 50%; }
.ft-dot-online { background: #52c41a; }
.ft-dot-busy { background: #faad14; }
.ft-dot-offline { background: #d9d9d9; }
.ft-id { font-size: 10px; font-family: 'SF Mono','Fira Code',monospace; color: #8c8c8c; }
.ft-right { }
.ft-time { font-size: 9px; color: #bfbfbf; font-family: monospace; }

/* ============================================================
   Modal
   ============================================================ */
.modal-mask {
  position: fixed; inset: 0; z-index: 100;
  background: rgba(0,0,0,.7);
  backdrop-filter: blur(10px);
  display: flex; align-items: center; justify-content: center;
  padding: 32px; animation: fadeIn .2s ease;
}
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.modal-box { position: relative; max-width: 90vw; max-height: 90vh; }
.modal-img { max-width: 100%; max-height: 85vh; border-radius: 8px; box-shadow: 0 20px 60px rgba(0,0,0,.5); }
.modal-x {
  position: absolute; top: -34px; right: -34px;
  width: 30px; height: 30px;
  display: flex; align-items: center; justify-content: center;
  border: none; border-radius: 50%;
  background: rgba(255,255,255,.1); color: rgba(255,255,255,.5);
  cursor: pointer; transition: all .2s;
}
.modal-x:hover { background: rgba(255,255,255,.2); color: #fff; }
.modal-x svg { width: 15px; height: 15px; }
.modal-title {
  position: absolute; top: -34px; left: 0;
  font-size: 10px; font-weight: 700; letter-spacing: .2em;
  color: rgba(255,255,255,.35);
}

/* Helper */
.hidden { display: none; }
.truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
