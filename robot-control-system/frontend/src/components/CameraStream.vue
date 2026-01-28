<template>
  <!-- 悬浮卡片容器 (默认右下角，避开底部控制栏) -->
  <div class="fixed bottom-32 right-8 z-50 w-80 md:w-96 rounded-3xl overflow-hidden shadow-[0_20px_60px_-15px_rgba(0,0,0,0.8)] border border-white/15 bg-zinc-900/80 backdrop-blur-xl animate-in slide-in-from-bottom-10 fade-in duration-500 ease-[cubic-bezier(0.32,0.72,0,1)]">
      

      <!-- Header (可拖拽区域) -->
      <div class="flex items-center justify-between px-4 py-3 bg-white/5 border-b border-white/5 cursor-move select-none">
        <div class="flex items-center gap-2.5">
          <!-- 录制指示灯 -->
          <div class="flex relative w-2.5 h-2.5">
             <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-75"></span>
             <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
          </div>
          <h3 class="text-white/90 text-[13px] font-medium tracking-wide font-['SF_Pro_Text']">{{ title }}</h3>
        </div>
        
        <!-- 窗口控制 -->
        <div class="flex items-center gap-2">
           <!-- 标定模式开关 -->
           <button @click="toggleCalibration" class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl transition-all active:scale-90 border" :class="isCalibrationMode ? 'text-primary bg-primary/10 border-primary/30 shadow-[0_0_15px_rgba(31,191,166,0.3)]' : 'text-zinc-400 bg-white/5 border-white/5 hover:bg-white/10'" title="标定模式">
             <span class="material-symbols-outlined text-[16px]">ads_click</span>
             <span class="text-[9px] font-bold tracking-wider">{{ isCalibrationMode ? '标定中' : '标定' }}</span>
           </button>
           <!-- 刷新按钮 -->
           <button @click="imgUrl = computedUrl() + '?t=' + Date.now()" class="p-1.5 rounded-full hover:bg-white/10 text-zinc-400 hover:text-white transition-all active:scale-90" title="刷新流">
             <span class="material-symbols-outlined text-[16px]">refresh</span>
           </button>
           <!-- 关闭按钮 -->
           <button @click="$emit('close')" class="p-1.5 rounded-full bg-white/10 hover:bg-white/20 text-zinc-300 hover:text-white transition-all active:scale-90">
             <span class="material-symbols-outlined text-[16px]">close</span>
           </button>
        </div>
      </div>

      <!-- Content -->
      <div class="relative aspect-[4/3] bg-black group cursor-crosshair" @click="handleImageClick">
        <!-- Loading State -->
        <div v-if="isLoading && !hasError" class="absolute inset-0 flex flex-col items-center justify-center text-zinc-500 gap-3 bg-zinc-900/50 backdrop-blur-sm z-10">
          <div class="w-6 h-6 border-2 border-white/20 border-t-white/80 rounded-full animate-spin"></div>
          <span class="text-[10px] font-medium tracking-wider opacity-70">CONNECTING</span>
        </div>

        <!-- Error State -->
        <div v-if="hasError" class="absolute inset-0 flex flex-col items-center justify-center bg-zinc-900 z-20 p-6 text-center">
          <div class="w-10 h-10 rounded-full bg-red-500/10 flex items-center justify-center mb-3">
             <span class="material-symbols-outlined text-red-500 text-xl">videocam_off</span>
          </div>
          <span class="text-xs text-zinc-400 mb-1">连接中断</span>
          <button @click="imgUrl = computedUrl() + '?t=' + Date.now()" class="mt-3 px-4 py-1.5 bg-white/10 hover:bg-white/20 rounded-full text-[10px] font-medium text-white transition-all hover:scale-105 active:scale-95">
            重试连接
          </button>
        </div>

        <!-- MJPEG Stream -->
        <img 
          ref="videoImg"
          :src="imgUrl" 
          alt="Camera Stream" 
          class="w-full h-full object-cover select-none pointer-events-none transition-opacity duration-500"
          :class="{ 'opacity-0': isLoading, 'brightness-75': isCalibrationMode }"
          @load="handleLoad"
          @error="handleError"
        />

        <!-- Calibration Hint Overlay -->
        <div v-if="isCalibrationMode" class="absolute inset-x-0 top-1/2 -translate-y-1/2 flex flex-col items-center justify-center p-4 pointer-events-none z-40">
           <div class="bg-primary/90 text-black px-4 py-2 rounded-xl text-[10px] font-bold tracking-widest shadow-2xl animate-bounce">
              点击画面中的目标进行标定
           </div>
           <div class="mt-2 bg-black/60 backdrop-blur-md text-white/70 px-3 py-1.5 rounded-lg text-[9px] font-medium border border-white/10 uppercase tracking-tighter">
              Click on the target point in the stream
           </div>
        </div>

        <!-- Click Marker (Calibration) -->
        <div v-if="clickPos" class="absolute w-4 h-4 border-2 border-primary rounded-full -translate-x-1/2 -translate-y-1/2 pointer-events-none z-30" :style="{ left: clickPos.x + 'px', top: clickPos.y + 'px' }">
           <div class="absolute inset-0 bg-primary/30 rounded-full animate-ping"></div>
        </div>

        <!-- Overlay Controls (Hover显示) -->
        <div class="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none flex flex-col justify-end p-4">
           <div class="flex justify-between items-end">
              <div class="flex flex-col gap-0.5">
                 <span class="text-[10px] text-white/80 font-mono">1920x1080</span>
                 <span class="text-[10px] font-medium" :class="statusColorClass">
                    {{ statusText }}
                 </span>
              </div>
           </div>
        </div>
      </div>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'

const props = defineProps({
  url: String,
  title: {
    type: String,
    default: 'Camera Stream'
  }
})

const emit = defineEmits(['close', 'calibration-click', 'loaded'])

const isLoading = ref(true)
const hasError = ref(false)
const imgUrl = ref('')
const videoImg = ref(null)

// Capture Snapshot for AI Detection
const captureSnapshot = async () => {
    if (!videoImg.value) return null
    
    try {
        const canvas = document.createElement('canvas')
        canvas.width = videoImg.value.naturalWidth || videoImg.value.width
        canvas.height = videoImg.value.naturalHeight || videoImg.value.height
        
        const ctx = canvas.getContext('2d')
        ctx.drawImage(videoImg.value, 0, 0, canvas.width, canvas.height)
        
        return new Promise((resolve) => {
            canvas.toBlob((blob) => {
                resolve({ 
                    blob, 
                    width: canvas.width, 
                    height: canvas.height 
                })
            }, 'image/jpeg', 0.8)
        })
    } catch (e) {
        console.error('Snapshot failed:', e)
        return null
    }
}

// Expose method to parent
defineExpose({
    captureSnapshot
})

// Calibration State
const isCalibrationMode = ref(false)
const clickPos = ref(null)

const toggleCalibration = () => {
    isCalibrationMode.value = !isCalibrationMode.value
    if (!isCalibrationMode.value) {
        clickPos.value = null
    }
}

const handleImageClick = (e) => {
    if (!isCalibrationMode.value || !videoImg.value) return
    
    // Get click position relative to image
    const rect = videoImg.value.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    
    // Update marker position
    clickPos.value = { x, y }
    
    // Calculate normalized coordinates (0.0 - 1.0)
    const u = x / rect.width
    const v = y / rect.height
    
    console.log(`Calibration Click: ${u.toFixed(3)}, ${v.toFixed(3)}`)
    emit('calibration-click', { u, v })
}

// Smart URL handling for IP Webcam
// Android IP Webcam app usage: http://IP:PORT/video for MJPEG stream
const computedUrl = () => {
  if (!props.url) return ''
  
  // Skip processing if it's our backend proxy
  if (props.url.includes('video_feed')) return props.url

  // If it's just the base URL, append /video for MJPEG stream (common standard)
  if (!props.url.includes('/video') && !props.url.includes('.mjpg')) {
     // Check if it ends with slash
     return props.url.endsWith('/') ? `${props.url}video` : `${props.url}/video`
  }
  return props.url
}

const handleLoad = () => {
  isLoading.value = false
  hasError.value = false
  emit('loaded')
}

const handleError = () => {
  isLoading.value = false
  hasError.value = true
}

watch(() => props.url, (newUrl) => {
  if (newUrl) {
    isLoading.value = true
    hasError.value = false
    imgUrl.value = computedUrl()
  }
}, { immediate: true })

// Camera Status Monitoring
const cameraConnected = ref(true)
let statusInterval = null

const checkStatus = async () => {
  try {
    const res = await fetch('http://localhost:5000/api/system/status')
    const data = await res.json()
    if (data.camera_connected !== undefined) {
      cameraConnected.value = data.camera_connected
    }
  } catch (e) {
    // If backend is down, we might want to show disconnected too
    // But cameraConnected refers to backend->camera connection.
    // If backend is down, the stream will fail anyway (hasError=true)
  }
}

const statusText = computed(() => {
    if (isCalibrationMode.value) return '● CALIBRATION MODE'
    if (hasError.value) return '● CONNECTION LOST'
    return cameraConnected.value ? '● LIVE' : '● DISCONNECTED'
})

const statusColorClass = computed(() => {
    if (isCalibrationMode.value) return 'text-primary'
    if (hasError.value) return 'text-red-500'
    return cameraConnected.value ? 'text-emerald-400' : 'text-red-500'
})

onMounted(() => {
    checkStatus()
    statusInterval = setInterval(checkStatus, 3000)
})

onUnmounted(() => {
    if (statusInterval) clearInterval(statusInterval)
})
</script>
