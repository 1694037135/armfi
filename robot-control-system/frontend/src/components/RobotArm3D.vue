<template>
  <div ref="container" class="robot-3d-container"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader'

const props = defineProps({
  jointAngles: { type: Array, default: () => [0, 0, 0, 0, 0, 0] }
})

// 添加：向父组件发送末端位置
const emit = defineEmits(['update:endEffectorPos'])

const container = ref(null)
let scene, camera, renderer, controls
let joints = {}
let axesHelper = null  // 坐标轴辅助线
let targetMesh = null // 目标位置指示器

function init() {
  scene = new THREE.Scene()
  // scene.background = new THREE.Color(0x0b1114)  // Removed for transparency

  camera = new THREE.PerspectiveCamera(60, container.value.clientWidth / container.value.clientHeight, 0.1, 1000)
  camera.position.set(0.5, 0.4, 0.5)

  // 1. 开启 Alpha 透明背景 (关键)
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setSize(container.value.clientWidth, container.value.clientHeight)
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  container.value.appendChild(renderer.domElement)

  controls = new OrbitControls(camera, renderer.domElement)
  // 3. 严格居中到原点
  controls.target.set(0, 0, 0)
  controls.enableDamping = true
  controls.dampingFactor = 0.08

  // 灯光
  scene.add(new THREE.AmbientLight(0xffffff, 0.6)) // 略微调暗环境光
  
  const mainLight = new THREE.DirectionalLight(0xffffff, 0.8) // 增强主光
  mainLight.position.set(5, 10, 5)
  mainLight.castShadow = true
  scene.add(mainLight)

  const fillLight = new THREE.DirectionalLight(0x1fbfa6, 0.4) // 自发光补光 (青色)
  fillLight.position.set(-5, 5, -5)
  scene.add(fillLight)

  // 地面网格
  const gridHelper = new THREE.GridHelper(4, 40, 0x1fbfa6, 0x233338) // 青色中心线，深灰网格
  scene.add(gridHelper)

  // 添加坐标轴辅助线（固定在世界坐标系原点）
  axesHelper = new THREE.AxesHelper(0.5)  // 0.5米长的坐标轴
  axesHelper.position.set(0, 0, 0)  // 固定在原点
  scene.add(axesHelper)

  // 目标位置指示器 (红色半透明球体)
  const targetGeometry = new THREE.SphereGeometry(0.03, 32, 32)
  const targetMaterial = new THREE.MeshBasicMaterial({ color: 0xff4444, transparent: true, opacity: 0.6 })
  targetMesh = new THREE.Mesh(targetGeometry, targetMaterial)
  targetMesh.visible = false
  scene.add(targetMesh)

  loadModel()
  animate()
}

function loadModel() {
  const loader = new GLTFLoader()
  
  console.log('🔍 开始加载3D模型: /models/robot-arm.glb')
  
  loader.load(
    '/models/robot-arm.glb',
    (gltf) => {
      console.log('✅ 模型加载成功！')
      const model = gltf.scene
      model.scale.set(1, 1, 1)
      model.position.set(0, 0, 0)
      
      model.traverse((child) => {
        if (child.isMesh) {
          child.castShadow = true
          child.receiveShadow = true
          // Apple 风格银灰色材质
          child.material = new THREE.MeshStandardMaterial({
            color: 0xc0c0c4,        // 银灰色
            metalness: 0.6,         // 金属感
            roughness: 0.35,        // 光滑度
          })
        }
      })
      
      scene.add(model)
      console.log('✅ 模型已添加到场景')
      
      // 查找关节
      joints.link1 = model.getObjectByName('link1001') || model.getObjectByName('link1')
      joints.link2 = model.getObjectByName('link2')
      joints.link3 = model.getObjectByName('link3')
      joints.link4 = model.getObjectByName('link4')
      joints.link5 = model.getObjectByName('link5')
      joints.link6 = model.getObjectByName('link6')
      
      // 自动归一化模型位置 (确保模型居中显示)
      const box = new THREE.Box3().setFromObject(model)
      
      if (!box.isEmpty()) {
        const center = box.getCenter(new THREE.Vector3())
        const size = box.getSize(new THREE.Vector3())
        
        // 核心修复: 将模型本身移动到世界原点 (0,0,0)
        // 抵消模型原本的偏移量，并让底部对齐地面 (Y=0)
        model.position.x = -center.x
        model.position.y = -box.min.y
        model.position.z = -center.z
        
        // 根据模型尺寸设定最佳观察距离
        const maxDim = Math.max(size.x, size.y, size.z) || 2
        const dist = maxDim * 1.5 // 1.5倍视距
        
        // 固定 ISO 视角，但基于模型尺寸缩放距离
        camera.position.set(dist, dist * 0.8, dist)
        camera.lookAt(0, size.y / 2, 0)
        
        // 控制器围绕模型中心旋转
        controls.target.set(0, size.y / 2, 0) 
      } else {
        console.warn('⚠️ 模型包围盒异常，使用默认视角')
        model.position.set(0, 0, 0)
        camera.position.set(2, 2, 2)
        camera.lookAt(0, 0, 0)
      }

      scene.add(model)
      
      // DEBUG: 添加坐标轴辅助线 - 确认场景渲染是否正常
      // scene.add(new THREE.AxesHelper(5)) 
      
      controls.update()
      
      console.log(`✅ 模型已重置位置至原点: ${model.position.x}, ${model.position.y}, ${model.position.z}`)
    },
    (progress) => {
      if (progress.total > 0) {
        const percent = (progress.loaded / progress.total * 100).toFixed(1)
        console.log(`📊 加载进度: ${percent}%`)
      }
    },
    (error) => {
      console.error('❌ 模型加载失败!')
      console.error('   错误信息:', error)
      console.error('   文件路径: /models/robot-arm.glb')
      console.error('   请检查:')
      console.error('   1. 文件是否存在于 public/models/ 目录')
      console.error('   2. 开发服务器是否正常运行')
      console.error('   3. 浏览器控制台是否有其他错误')
    }
  )
}

function animate() {
  requestAnimationFrame(animate)
  
  const a = props.jointAngles
  
  // 更新关节角度
  if (joints.link1) joints.link1.rotation.z = a[0]  // 底座
  if (joints.link2) joints.link2.rotation.x = a[1]  // 肩部
  if (joints.link3) joints.link3.rotation.x = a[2]  // 肘部
  if (joints.link4) joints.link4.rotation.x = a[3]  // 腕部1
  if (joints.link5) joints.link5.rotation.x = a[4]  // 腕部2
  if (joints.link6) joints.link6.rotation.y = a[5]  // 末端
  
  // 更新目标指示球位置
  if (props.targetPos && targetMesh) {
    targetMesh.position.set(props.targetPos.x, props.targetPos.y, props.targetPos.z)
    targetMesh.visible = true
  } else if (targetMesh) {
    targetMesh.visible = false
  }

  // 计算末端位置（如果link6存在）
  if (joints.link6) {
    const endEffectorPos = new THREE.Vector3()
    joints.link6.getWorldPosition(endEffectorPos)
    
    // 发送末端位置给父组件
    emit('update:endEffectorPos', {
      x: endEffectorPos.x.toFixed(3),
      y: endEffectorPos.y.toFixed(3),
      z: endEffectorPos.z.toFixed(3)
    })
  }
  
  controls.update()
  renderer.render(scene, camera)
}

function handleResize() {
  if (container.value && camera && renderer) {
    camera.aspect = container.value.clientWidth / container.value.clientHeight
    camera.updateProjectionMatrix()
    renderer.setSize(container.value.clientWidth, container.value.clientHeight)
  }
}

onMounted(() => {
  init()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (renderer) renderer.dispose()
})
</script>

<style scoped>
.robot-3d-container {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  overflow: hidden;
  background: transparent;
  pointer-events: auto;
}
</style>
