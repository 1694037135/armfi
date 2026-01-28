<template>
  <div class="glass-panel-log p-0 w-80 relative overflow-hidden transition-all duration-300 hover:shadow-[0_8px_48px_rgba(0,217,255,0.15)] group h-64">
    
    <!-- 标题栏 (绝对定位在左上角) -->
    <div class="absolute top-4 left-4 z-20 flex items-center gap-3 pointer-events-none">
       <div class="w-2 h-2 rounded-full bg-primary animate-pulse shadow-[0_0_8px_rgba(0,217,255,0.6)]"></div>
       <h3 class="text-sm font-bold text-zinc-300 tracking-wide group-hover:text-primary transition-colors">末端空间坐标</h3>
    </div>

    <!-- 3D 容器 -->
    <div ref="container" class="w-full h-full bg-gradient-to-b from-transparent to-black/20"></div>


    <!-- 数值覆盖层 (右侧) - HIDDEN: FK calculation buggy -->
    <!--
    <div class="absolute top-12 right-2 z-20 flex flex-col gap-1 pointer-events-none">
        <div class="flex items-center justify-end gap-2 px-3 py-1 bg-black/40 rounded-lg border border-red-500/20 backdrop-blur-sm shadow-sm">
            <span class="text-xs font-bold text-red-500">X</span>
            <span class="font-mono text-sm text-white min-w-[4em] text-right">{{ Number(position.x).toFixed(3) }}</span>
        </div>
        <div class="flex items-center justify-end gap-2 px-3 py-1 bg-black/40 rounded-lg border border-green-500/20 backdrop-blur-sm shadow-sm">
            <span class="text-xs font-bold text-green-500">Y</span>
            <span class="font-mono text-sm text-white min-w-[4em] text-right">{{ Number(position.y).toFixed(3) }}</span>
        </div>
        <div class="flex items-center justify-end gap-2 px-3 py-1 bg-black/40 rounded-lg border border-blue-500/20 backdrop-blur-sm shadow-sm">
            <span class="text-xs font-bold text-blue-500">Z</span>
            <span class="font-mono text-sm text-white min-w-[4em] text-right">{{ Number(position.z).toFixed(3) }}</span>
        </div>
    </div>
    -->
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls'

const props = defineProps({
  position: {
    type: Object,
    default: () => ({ x: 0, y: 0, z: 0 })
  },
  targetPosition: {
    type: Object,
    default: null
  }
})

const container = ref(null)
let scene, camera, renderer, controls
let marker, targetMarker, connectorLine
// 投影线引用
let lineX, lineY, lineZ

function init() {
  if (!container.value) return
  const width = container.value.clientWidth
  const height = container.value.clientHeight

  scene = new THREE.Scene()
  
  // 透视相机
  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100)
  camera.position.set(2.5, 2.0, 2.5) // 调整视角
  camera.lookAt(0, 0, 0)

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setSize(width, height)
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.setClearColor(0x000000, 0) // 透明背景
  container.value.appendChild(renderer.domElement)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  controls.enableZoom = false 
  controls.enablePan = false
  controls.autoRotate = true 
  controls.autoRotateSpeed = 1.0
  controls.target.set(0, 0, 0)

  // 1. 坐标轴 (长度 1.5)
  const axesHelper = new THREE.AxesHelper(1.5)
  scene.add(axesHelper)

  // 2. 网格 (XZ平面 - YUp) -> ThreeJS GridHelper 默认是 XZ 平面
  // Adjust grid color to be subtle
  const gridHelper = new THREE.GridHelper(3, 10, 0x333333, 0x111111)
  scene.add(gridHelper)

  // 3. 目标点标记 (Current Position - Cyan)
  const geometry = new THREE.SphereGeometry(0.06, 16, 16)
  const material = new THREE.MeshBasicMaterial({ color: 0x00ffff }) 
  marker = new THREE.Mesh(geometry, material)
  
  // 外发光层
  const glowGeo = new THREE.SphereGeometry(0.12, 16, 16)
  const glowMat = new THREE.MeshBasicMaterial({ 
      color: 0x00ffff, 
      transparent: true, 
      opacity: 0.25 
  })
  const glow = new THREE.Mesh(glowGeo, glowMat)
  marker.add(glow)
  scene.add(marker)

  // 3.1 目标影子标记 (Target Position - Red Ghost)
  const targetGeo = new THREE.SphereGeometry(0.06, 16, 16)
  const targetMat = new THREE.MeshBasicMaterial({ color: 0xff0000, transparent: true, opacity: 0.6, wireframe: true })
  targetMarker = new THREE.Mesh(targetGeo, targetMat)
  targetMarker.visible = false // Initially hidden
  scene.add(targetMarker)

  // 3.2 连接线 (Current -> Target)
  const lineGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0,0,0), new THREE.Vector3(0,0,0)])
  const connectorMat = new THREE.LineDashedMaterial({
      color: 0xffffff,
      dashSize: 0.1,
      gapSize: 0.05,
      opacity: 0.5,
      transparent: true
  })
  connectorLine = new THREE.Line(lineGeo, connectorMat)
  connectorLine.visible = false
  scene.add(connectorLine)

  // 4. 投影线 (辅助理解三维位置)
  const lineMat = new THREE.LineDashedMaterial({
      color: 0xffffff,
      dashSize: 0.05,
      gapSize: 0.05,
      opacity: 0.3,
      transparent: true
  })
  
  // Point to Ground (XZ plane, y=0)
  const geomY = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0,0,0), new THREE.Vector3(0,0,0)])
  lineY = new THREE.Line(geomY, lineMat)
  lineY.computeLineDistances() // enable dashed
  scene.add(lineY)

  window.addEventListener('resize', handleResize)
  
  // Use ResizeObserver to handle container size changes (e.g. animation finish)
  const resizeObserver = new ResizeObserver(() => handleResize())
  resizeObserver.observe(container.value)
  
  animate()
}

function updateMarker() {
    if (!marker) return

    // 获取当前坐标
    let x = parseFloat(props.position.x) || 0
    let y = parseFloat(props.position.y) || 0
    let z = parseFloat(props.position.z) || 0

    marker.position.set(x, y, z)

    // 更新投影线: 从点 (x,y,z) 到地面 (x,0,z)
    if (lineY) {
        const positions = lineY.geometry.attributes.position.array
        // Start point (Marker)
        positions[0] = x
        positions[1] = y
        positions[2] = z
        // End point (Ground)
        positions[3] = x
        positions[4] = 0 // Ground Y
        positions[5] = z
        lineY.geometry.attributes.position.needsUpdate = true
        lineY.computeLineDistances()
    }

    // 更新目标点和连接线
    if (props.targetPosition) {
        let tx = parseFloat(props.targetPosition.x) || 0
        let ty = parseFloat(props.targetPosition.y) || 0
        let tz = parseFloat(props.targetPosition.z) || 0
        
        targetMarker.position.set(tx, ty, tz)
        targetMarker.visible = true
        
        // Update connector line
        const linePos = connectorLine.geometry.attributes.position.array
        linePos[0] = x; linePos[1] = y; linePos[2] = z
        linePos[3] = tx; linePos[4] = ty; linePos[5] = tz
        connectorLine.geometry.attributes.position.needsUpdate = true
        connectorLine.computeLineDistances()
        connectorLine.visible = true
    } else {
        targetMarker.visible = false
        connectorLine.visible = false
    }
}

function handleResize() {
    if (!container.value || !camera || !renderer) return
    const width = container.value.clientWidth
    const height = container.value.clientHeight
    
    if (width === 0 || height === 0) return

    camera.aspect = width / height
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)
}

function animate() {
  requestAnimationFrame(animate)
  if (controls) controls.update()
  updateMarker()
  if (renderer && scene && camera) renderer.render(scene, camera)
}

onMounted(() => {
  // Delay init slightly to skip initial 0-size state if any
  setTimeout(init, 100)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (renderer) {
      renderer.dispose()
      renderer.forceContextLoss()
  }
})
</script>

<style scoped>
</style>
