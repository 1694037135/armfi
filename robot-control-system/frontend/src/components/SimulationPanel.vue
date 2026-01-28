<template>
  <div class="fixed z-[70] w-80 glass-panel-hint p-6 shadow-2xl" :style="panelStyle">
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-2">
        <span class="material-symbols-outlined text-primary">monitor_heart</span>
        <span class="text-sm font-bold text-zinc-300">MuJoCo 仿真</span>
      </div>
      <button class="p-2 rounded-md bg-white/10 hover:bg-white/20" @click="emit('close')">
        <span class="material-symbols-outlined text-zinc-400">close</span>
      </button>
    </div>
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/5">
        <span class="relative flex h-1.5 w-1.5">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" :class="connOpen ? 'bg-emerald-400' : 'bg-red-400'"></span>
          <span class="relative inline-flex rounded-full h-1.5 w-1.5" :class="connOpen ? 'bg-emerald-500' : 'bg-red-500'"></span>
        </span>
        <span class="text-xs font-medium" :class="connOpen ? 'text-zinc-300' : 'text-red-400'">{{ connOpen ? 'Connected' : 'Disconnected' }}</span>
      </div>
      <div class="flex items-center gap-2">
        <button v-if="!connOpen" class="px-3 py-1 rounded-full border bg-white/5 border-white/10 text-zinc-300 hover:bg-white/10 text-xs font-bold transition-all active:scale-95" @click="retryConnect">
          重连
        </button>
        <div class="px-3 py-1 rounded-full border" :class="runStateClass">
          <span class="text-xs font-mono">{{ runStateLabel }}</span>
        </div>
      </div>
    </div>
    <div class="grid grid-cols-3 gap-3 mb-4">
      <div class="flex flex-col items-center gap-1 bg-black/20 rounded-xl p-3 border border-white/10">
        <span class="text-[10px] text-zinc-500">Step</span>
        <span class="font-mono text-lg text-white">{{ metrics.step }}</span>
      </div>
      <div class="flex flex-col items-center gap-1 bg-black/20 rounded-xl p-3 border border-white/10">
        <span class="text-[10px] text-zinc-500">Distance</span>
        <span class="font-mono text-lg text-white">{{ formattedDistance }}</span>
      </div>
      <div class="flex flex-col items-center gap-1 bg-black/20 rounded-xl p-3 border border-white/10">
        <span class="text-[10px] text-zinc-500">Final</span>
        <span class="font-mono text-lg text-white">{{ formattedFinal }}</span>
      </div>
    </div>
    <div v-if="lastEvent" class="mb-3 px-3 py-2 rounded-lg border" :class="eventClass">
      <div class="flex items-center gap-2">
        <span class="material-symbols-outlined text-sm" :class="eventIconColor">{{ eventIcon }}</span>
        <span class="text-xs font-medium">{{ lastEventText }}</span>
      </div>
    </div>
    <div class="flex items-center gap-2 mb-3">
      <input v-model.number="target.x" type="number" step="0.01" class="w-20 px-2 py-1 bg-white/10 border border-white/10 rounded text-xs text-white font-mono" placeholder="x">
      <input v-model.number="target.y" type="number" step="0.01" class="w-20 px-2 py-1 bg-white/10 border border-white/10 rounded text-xs text-white font-mono" placeholder="y">
      <input v-model.number="target.z" type="number" step="0.01" class="w-20 px-2 py-1 bg-white/10 border border-white/10 rounded text-xs text-white font-mono" placeholder="z">
      <button class="px-3 py-1 rounded bg-primary text-black text-xs font-bold hover:bg-primary/90" @click="applyTarget">设定</button>
    </div>
    <div class="grid grid-cols-3 gap-2">
      <button class="px-3 py-2 rounded-lg bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs font-bold hover:bg-emerald-500/30" @click="start">Start</button>
      <button class="px-3 py-2 rounded-lg bg-amber-500/20 border border-amber-500/40 text-amber-300 text-xs font-bold hover:bg-amber-500/30" @click="stop">Stop</button>
      <button class="px-3 py-2 rounded-lg bg-zinc-800/40 border border-white/10 text-white text-xs font-bold hover:bg-zinc-700/40" @click="reset">Reset</button>
    </div>
  </div>
</template>
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  anchorRect: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close'])

const wsUrl = (import.meta.env.VITE_MUJOCO_WS && import.meta.env.VITE_MUJOCO_WS.trim() !== '') ? import.meta.env.VITE_MUJOCO_WS : 'ws://localhost:5000/ws/mujoco'
const connOpen = ref(false)
const running = ref(false)
const completed = ref(false)
const metrics = ref({ step: 0, distance: 0, finalDistance: null })
const lastEvent = ref(null)
const target = ref({ x: 0.1, y: -0.25, z: 0.3 })
let ws = null
const wasEverConnected = ref(false)

const panelStyle = computed(() => {
  const fallback = {
    top: '6rem',
    right: '2rem',
    transformOrigin: 'top right'
  }
  if (!props.anchorRect) return fallback

  const rect = props.anchorRect
  const panelWidth = 320
  const pad = 12
  const top = Math.max(12, rect.bottom + 10)
  const right = Math.max(12, Math.min((window.innerWidth ?? 0) - 12 - panelWidth, (window.innerWidth ?? 0) - rect.right))

  const originX = `calc(100% - ${Math.max(10, rect.width / 2)}px)`
  const originY = `${Math.min(-8, -(rect.height / 2 + 10))}px`

  return {
    top: `${top}px`,
    right: `${right}px`,
    transformOrigin: `${originX} ${originY}`
  }
})

const formattedDistance = computed(() => metrics.value.distance?.toFixed(3))
const formattedFinal = computed(() => metrics.value.finalDistance != null ? Number(metrics.value.finalDistance).toFixed(3) : '--')
const runStateLabel = computed(() => completed.value ? 'Completed' : (running.value ? 'Running' : 'Idle'))
const runStateClass = computed(() => completed.value ? 'bg-emerald-500/10 border border-emerald-500/40 text-emerald-300' : (running.value ? 'bg-primary/10 border border-primary/40 text-primary' : 'bg-white/5 border border-white/10 text-zinc-300'))
const eventIcon = computed(() => {
  if (!lastEvent.value) return ''
  const t = lastEvent.value.type
  if (t === 'completed') return 'military_tech'
  if (t === 'warning') return 'warning'
  if (t === 'error') return 'error'
  return 'info'
})
const eventIconColor = computed(() => {
  if (!lastEvent.value) return 'text-zinc-400'
  const t = lastEvent.value.type
  if (t === 'completed') return 'text-emerald-400'
  if (t === 'warning') return 'text-amber-400'
  if (t === 'error') return 'text-red-400'
  return 'text-zinc-400'
})
const eventClass = computed(() => {
  if (!lastEvent.value) return 'border-white/10 text-zinc-300'
  const t = lastEvent.value.type
  if (t === 'completed') return 'border-emerald-500/40 text-emerald-300 bg-emerald-500/10'
  if (t === 'warning') return 'border-amber-500/40 text-amber-300 bg-amber-500/10'
  if (t === 'error') return 'border-red-500/40 text-red-300 bg-red-500/10'
  return 'border-white/10 text-zinc-300'
})
const lastEventText = computed(() => {
  if (!lastEvent.value) return ''
  const e = lastEvent.value
  if (e.type === 'completed') return `完成: 步数 ${e.steps}, 距离 ${Number(e.final_distance ?? e.finalDistance ?? 0).toFixed(3)}`
  if (e.type === 'warning' || e.type === 'error') return e.message || e.type
  if (e.type === 'started') return '仿真开始'
  if (e.type === 'stopped') return '仿真停止'
  if (e.type === 'reset') return '已重置'
  if (e.type === 'target_set') return `目标: ${e.target?.map(v=>Number(v).toFixed(3)).join(', ')}`
  return e.type
})
function connectWS() {
  try {
    lastEvent.value = { type: 'info', message: `连接中: ${wsUrl}` }
    ws = new WebSocket(wsUrl)
    ws.onopen = () => {
      connOpen.value = true
      wasEverConnected.value = true
      completed.value = false
      running.value = false
      lastEvent.value = { type: 'connected' }
    }
    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data)
        if (data.type === 'joint_update') {
          metrics.value.step = data.step ?? metrics.value.step
          metrics.value.distance = data.distance ?? metrics.value.distance
          if (Array.isArray(data.target_pos)) {
            const [x, y, z] = data.target_pos
            const t = { x, y, z }
            target.value = t
            emitTarget(t)
          }
        } else if (data.type === 'completed') {
          running.value = false
          completed.value = true
          metrics.value.finalDistance = data.final_distance ?? data.finalDistance ?? metrics.value.finalDistance
          lastEvent.value = data
        } else if (data.type === 'started') {
          running.value = true
          completed.value = false
          lastEvent.value = data
        } else if (data.type === 'stopped' || data.type === 'reset') {
          running.value = false
          lastEvent.value = data
        } else if (data.type === 'warning' || data.type === 'error') {
          lastEvent.value = data
        } else if (data.type === 'target_set') {
          lastEvent.value = data
          if (Array.isArray(data.target)) {
            const [x, y, z] = data.target
            const t = { x, y, z }
            target.value = t
            emitTarget(t)
          }
        }
      } catch {}
    }
    ws.onclose = () => {
      connOpen.value = false
      running.value = false
      if (wasEverConnected.value) {
        lastEvent.value = { type: 'warning', message: '连接已断开' }
      } else {
        lastEvent.value = { type: 'error', message: `无法连接: ${wsUrl}` }
      }
    }
    ws.onerror = () => {
      lastEvent.value = { type: 'error', message: `WebSocket 连接失败: ${wsUrl}` }
    }
  } catch {}
}
function retryConnect() {
  try { ws && ws.close() } catch {}
  connOpen.value = false
  running.value = false
  completed.value = false
  connectWS()
}
function send(obj) {
  if (ws && connOpen.value) ws.send(JSON.stringify(obj))
}
function start() {
  send({ action: 'start' })
}
function stop() {
  send({ action: 'stop' })
}
function reset() {
  send({ action: 'reset' })
  metrics.value = { step: 0, distance: 0, finalDistance: null }
  completed.value = false
}
function applyTarget() {
  const t = [Number(target.value.x), Number(target.value.y), Number(target.value.z)]
  send({ action: 'set_target', target: t })
}
function emitTarget(t) {
  const payload = { x: Number(t.x), y: Number(t.y), z: Number(t.z) }
  if (payload && typeof payload.x === 'number') {
    const e = new CustomEvent('target-update', { detail: payload })
    window.dispatchEvent(e)
  }
}
onMounted(() => {
  connectWS()
  window.addEventListener('beforeunload', stop)
})
onUnmounted(() => {
  try { stop() } catch {}
  try { ws && ws.close() } catch {}
})
</script>
