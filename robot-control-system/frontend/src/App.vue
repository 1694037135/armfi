<template>
  <div class="h-screen w-full bg-[#050505] text-white overflow-hidden font-['PingFang_SC',_-apple-system,_BlinkMacSystemFont,_'Helvetica_Neue',_sans-serif] selection:bg-primary selection:text-black antialiased relative">
    
    <!-- 3D 场景背景 (Z-Index 0) -->
    <div class="absolute inset-0 z-0 bg-[#050505]">
       
       <!-- 1. 底层视觉特效 (现在位于模型下方) -->
       <div class="absolute inset-0 pointer-events-none overflow-hidden">
          <!-- 科技网格 -->
          <div class="absolute inset-0 bg-tech-grid opacity-20"></div>
          
          <!-- 全息舞台中心特效 -->
          <div class="absolute inset-0 flex items-center justify-center">
             <div class="relative w-[800px] h-[800px] opacity-30">
                <!-- 动态呼吸圆环 (Core Pulse) -->
                <div class="absolute inset-0 opacity-20 border border-primary/40 rounded-full scale-100 animate-pulse"></div>
                
                <!-- 新增:多重科技圆环 (Complex Interwoven Geometry) -->
                <div class="absolute inset-0 opacity-10 border border-primary/30 rounded-full scale-[1.3] border-dashed animate-[spin_60s_linear_infinite]"></div>
                <div class="absolute inset-0 opacity-5 border border-white/20 rounded-full scale-[1.6]"></div>
                <!-- 偏心圆环效果 -->
                <div class="absolute inset-0 opacity-10 border-t border-b border-primary/20 rounded-full scale-[1.9] rotate-45"></div>
                
                <div class="absolute inset-0 opacity-10 border-2 border-primary/10 rounded-full scale-[2.2] border-dotted animate-[spin_120s_linear_infinite_reverse]"></div>
                
                <!-- 大范围装饰线 -->
                <div class="absolute inset-0 opacity-5 border border-primary/20 rounded-full scale-[2.8]"></div>
                <div class="absolute inset-0 opacity-5 border-l border-r border-white/10 rounded-full scale-[3.2]"></div>
                
                <div class="absolute inset-0 opacity-5 border border-primary/20 rounded-full scale-[0.7]"></div>
                
                <!-- 十字准星 (Crosshair) - 居中定位 -->
                <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-px h-[600px] bg-gradient-to-b from-transparent via-primary/50 to-transparent crosshair-glow"></div>
                <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-px w-[600px] bg-gradient-to-r from-transparent via-primary/50 to-transparent crosshair-glow"></div>
                
                <!-- 球形虚线点阵 -->
                <div class="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(31,191,166,0.1)_1px,transparent_1px)] bg-[size:40px_40px] rounded-full mask-radial"></div>
             </div>
          </div>
       </div>

       <!-- 2. 3D 机械臂 (顶层 - 确保位于特效之上) -->
       <RobotArm3D 
         :jointAngles="displayAngles" 
         :targetPos="targetEndEffectorPos"
         @update:endEffectorPos="endEffectorPos = $event"
         class="absolute inset-0 z-50 pointer-events-auto" 
       />
    </div>

    <!-- 顶部导航栏 -->
    <header class="fixed top-0 left-0 w-full z-[100] flex items-center justify-between px-8 py-6 pointer-events-none animate-[slideDown_0.8s_ease-out_forwards]">
      <div class="flex items-center gap-4 pointer-events-auto glass-panel-header px-6 py-3 shadow-2xl hover:scale-105 transition-transform duration-300">
        <span class="material-symbols-outlined text-primary text-2xl">precision_manufacturing</span>
        <div class="h-4 w-px bg-white/10 mx-1"></div>
        <h1 class="text-white font-semibold tracking-tight text-base">机械臂控制系统 <span class="text-zinc-500 font-normal text-sm">v1.0</span></h1>
        
        <div class="flex items-center gap-2 ml-4 px-3 py-1 rounded-full bg-white/5 border border-white/5">
          <span class="relative flex h-1.5 w-1.5">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" :class="connected ? 'bg-emerald-400' : 'bg-red-400'"></span>
            <span class="relative inline-flex rounded-full h-1.5 w-1.5" :class="connected ? 'bg-emerald-500' : 'bg-red-500'"></span>
          </span>
          <span class="text-sm font-medium tracking-wide" :class="connected ? 'text-zinc-300' : 'text-red-400'">
             {{ connected ? '系统在线' : (isDemoMode ? 'Demomode' : '离线状态') }}
          </span>
        </div>
      </div>
      
      <!-- 右侧功能区 -->
      <div class="flex items-center gap-4 pointer-events-auto">
        <!-- 控制mode切换 -->
        <div class="glass-panel-header px-4 py-2 shadow-2xl flex items-center gap-3 hover:scale-105 transition-transform duration-300">
          <button 
            @click="toggleControlMode"
            class="flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all duration-300"
            :class="controlMode === 'physical' 
              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' 
              : 'bg-white/5 text-zinc-400 border border-white/10 hover:bg-white/10 hover:text-white'"
            :title="controlMode === 'simulation' ? '点击Switched toPhysical Mode' : '点击Switched toSimulation Mode'"
          >
            <span class="material-symbols-outlined text-lg">
              {{ controlMode === 'physical' ? 'precision_manufacturing' : 'view_in_ar' }}
            </span>
            <span class="text-sm font-medium">
              {{ controlMode === 'physical' ? '实物' : 'simulation' }}
            </span>
            <span 
              class="w-2 h-2 rounded-full animate-pulse"
              :class="controlMode === 'physical' ? 'bg-emerald-400' : 'bg-zinc-500'"
            ></span>
          </button>
          <div v-if="!isPhysicalAvailable && controlMode === 'physical'" class="text-xs text-amber-400">
            (串口未连接)
          </div>
        </div>
        
        <div class="glass-panel-header px-6 py-3 shadow-2xl flex items-center gap-6 hover:scale-105 transition-transform duration-300">
          <div class="flex flex-col items-end">
            <span class="text-sm text-zinc-500 font-medium tracking-wider">本次会话</span>
            <span class="font-mono text-zinc-200 text-lg tracking-tight">{{ runningTime }}</span>
          </div>
          <div class="h-8 w-px bg-white/10"></div>
          <button class="p-2 hover:bg-white/10 rounded-full transition-all duration-300 text-zinc-400 hover:text-white hover:rotate-90" @click="showKeyHints = !showKeyHints" :class="{ 'text-primary': showKeyHints }">
            <span class="material-symbols-outlined text-xl">keyboard</span>
          </button>
          <button class="p-2 hover:bg-white/10 rounded-full transition-all duration-300 text-zinc-400 hover:text-white" @click="runTestSequence" title="功能测试">
            <span class="material-symbols-outlined text-xl">science</span>
          </button>
        </div>
      </div>
    </header>


    <!-- 左侧面板容器 -->
    <div class="fixed top-32 left-8 bottom-64 z-[60] flex flex-col gap-4 pointer-events-none w-[28rem]">
       <!-- System Logs -->
        <div class="glass-panel-log p-6 shrink-0 animate-[fadeInLeft_0.8s_ease-out_forwards] pointer-events-auto">
           <div @click="drawerCollapsed = !drawerCollapsed" class="flex items-center justify-between mb-5 cursor-pointer group hover:bg-white/5 -m-2 p-2 rounded-xl transition-all duration-300">
              <h2 class="text-lg font-bold tracking-wide text-white group-hover:text-primary transition-colors">SYSTEM LOGS</h2>
              <div class="w-7 h-7 rounded-full bg-white/5 flex items-center justify-center group-hover:bg-white/10 transition-colors">
                <span class="material-symbols-outlined text-zinc-500 group-hover:text-primary text-base transform transition-transform duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)]" :class="{ 'rotate-180': !drawerCollapsed }">expand_more</span>
             </div>
          </div>
          
          <div class="grid transition-[grid-template-rows] duration-500 ease-[cubic-bezier(0.32,0.72,0,1)]"
               :class="drawerCollapsed ? 'grid-rows-[0fr]' : 'grid-rows-[1fr]'">
             <div class="overflow-hidden">
                 <div class="px-5 pb-5 space-y-2 font-sans text-sm h-48 overflow-y-auto scrollbar-thin mask-log-content pr-2 leading-relaxed">
                   <div v-for="(log, i) in logs" :key="i" class="flex gap-3 animate-in slide-in-from-left-2 fade-in duration-300 p-2 rounded-lg hover:bg-white/5 transition-colors border border-transparent hover:border-white/5">
                      <span class="text-zinc-400 shrink-0 font-medium">{{ log.time }}</span>
                      <span class="font-medium tracking-wide" :class="log.type === 'error' ? 'text-red-400' : (log.type === 'success' ? 'text-emerald-400' : 'text-zinc-200')">{{ log.message }}</span>
                   </div>
                </div>
             </div>
          </div>
       </div>

       <!-- DeepSeek AI Panel -->
       <DeepSeekPanel 
         class="animate-[fadeInLeft_0.9s_ease-out_forwards]"
         :messages="deepSeekMessages"
         :is-processing="isDeepSeekProcessing"
         @send="handleDeepSeekSend"
       />
    </div>

    <!-- 底部控制台 -->
    <main class="fixed bottom-12 left-0 right-0 z-[100] flex justify-center items-end px-4 sm:px-10 pointer-events-none animate-[slideUp_1s_cubic-bezier(0.16,1,0.3,1)_0.5s_forwards]">
      <div class="glass-panel py-8 px-16 shadow-2xl flex flex-nowrap items-center justify-center gap-12 pointer-events-auto transform transition-transform hover:scale-[1.005] duration-500 w-full max-w-[2000px] overflow-hidden">
        
        <!-- Section 1: 末端执行器 -->
        <div class="flex flex-col justify-center items-center gap-4 min-w-[220px] shrink-0">
           <span class="text-lg font-bold text-zinc-200 tracking-wide">末端执行器</span>
           <div class="flex items-center gap-6">
              <!-- 开关按钮 -->
              <button @click="toggleGripper(!gripperOpen)" class="w-20 h-10 rounded-full relative transition-all duration-300 shadow-inner border border-white/5 hover:scale-105 active:scale-95 ease-[cubic-bezier(0.25,0.1,0.25,1)]" :class="gripperOpen ? 'bg-emerald-500/20' : 'bg-black/40'">
                 <div class="absolute top-1 left-1 w-8 h-8 bg-white rounded-full shadow-md transform transition-transform duration-300" :class="gripperOpen ? 'translate-x-10 bg-emerald-400' : 'translate-x-0 bg-zinc-400'"></div>
              </button>
              <div class="flex gap-3">
                 <button class="force-animate-btn group w-14 h-14" @mousedown="pressKey('u')" @mouseup="releaseKey('u')" @mouseleave="releaseKey('u')" :class="{ 'active': activeKeys.has('u') }">
                    <span class="material-symbols-outlined text-zinc-400 group-hover:text-white text-3xl">rotate_left</span>
                 </button>
                 <button class="force-animate-btn group w-14 h-14" @mousedown="pressKey('o')" @mouseup="releaseKey('o')" @mouseleave="releaseKey('o')" :class="{ 'active': activeKeys.has('o') }">
                    <span class="material-symbols-outlined text-zinc-400 group-hover:text-white text-3xl">rotate_right</span>
                 </button>
              </div>
           </div>
        </div>

        <!-- Section 2: 主轴控制 -->
        <div class="flex flex-nowrap items-center justify-center gap-14 px-10 xl:border-x border-white/5 shrink-0">
           <!-- 关节 1 -->
           <div class="flex flex-col items-center gap-4">
               <span class="text-lg font-bold text-zinc-200">基座旋转</span>
              <div class="flex items-center gap-6">
                 <button class="control-btn w-14 h-14" @mousedown="pressKey('a')" @mouseup="releaseKey('a')" @mouseleave="releaseKey('a')" :class="{ 'active': activeKeys.has('a') }">
                    <span class="material-symbols-outlined text-3xl">chevron_left</span>
                 </button>
                 <span class="w-28 text-center font-mono text-3xl font-medium tracking-tight tabular-nums text-white">{{ (displayAngles[0] * 180 / Math.PI).toFixed(1) }}°</span>
                 <button class="control-btn w-14 h-14" @mousedown="pressKey('d')" @mouseup="releaseKey('d')" @mouseleave="releaseKey('d')" :class="{ 'active': activeKeys.has('d') }">
                    <span class="material-symbols-outlined text-3xl">chevron_right</span>
                 </button>
              </div>
           </div>
           
           <!-- 关节 2 -->
           <div class="flex flex-col items-center gap-4">
              <span class="text-lg font-bold text-zinc-200">大臂俯仰</span>
              <div class="flex items-center gap-6">
                 <button class="control-btn w-14 h-14" @mousedown="pressKey('s')" @mouseup="releaseKey('s')" @mouseleave="releaseKey('s')" :class="{ 'active': activeKeys.has('s') }">
                    <span class="material-symbols-outlined text-3xl">expand_more</span>
                 </button>
                 <span class="w-28 text-center font-mono text-3xl font-medium tracking-tight tabular-nums text-white">{{ (displayAngles[1] * 180 / Math.PI).toFixed(1) }}°</span>
                 <button class="control-btn w-14 h-14" @mousedown="pressKey('w')" @mouseup="releaseKey('w')" @mouseleave="releaseKey('w')" :class="{ 'active': activeKeys.has('w') }">
                    <span class="material-symbols-outlined text-3xl">expand_less</span>
                 </button>
              </div>
           </div>
        </div>

        <div class="flex flex-nowrap items-center justify-center gap-12 shrink-0">
          <!-- Section 3: 精密轴控制 -->
          <div class="grid grid-cols-3 gap-12 shrink-0">
              <!-- 关节 3 -->
              <div class="flex flex-col items-center gap-3">
                 <span class="text-base font-bold text-zinc-200">从臂</span>
                 <div class="bg-black/30 rounded-2xl p-2 flex justify-center gap-2 border border-white/5">
                    <button class="force-animate-btn w-14 h-14" @mousedown="pressKey('f')" @mouseup="releaseKey('f')" @mouseleave="releaseKey('f')" :class="{ 'active': activeKeys.has('f') }">
                      <span class="text-2xl font-bold">-</span>
                    </button>
                    <button class="force-animate-btn w-14 h-14" @mousedown="pressKey('r')" @mouseup="releaseKey('r')" @mouseleave="releaseKey('r')" :class="{ 'active': activeKeys.has('r') }">
                      <span class="text-2xl font-bold">+</span>
                    </button>
                 </div>
              </div>
              <!-- 关节 4 -->
              <div class="flex flex-col items-center gap-3">
                 <span class="text-base font-bold text-zinc-200">手腕旋转</span>
                 <div class="bg-black/30 rounded-2xl p-2 flex justify-center gap-2 border border-white/5">
                    <button class="force-animate-btn w-14 h-14" @mousedown="pressKey('k')" @mouseup="releaseKey('k')" @mouseleave="releaseKey('k')" :class="{ 'active': activeKeys.has('k') }">
                      <span class="text-2xl font-bold">↺</span>
                    </button>
                    <button class="force-animate-btn w-14 h-14" @mousedown="pressKey('i')" @mouseup="releaseKey('i')" @mouseleave="releaseKey('i')" :class="{ 'active': activeKeys.has('i') }">
                      <span class="text-2xl font-bold">↻</span>
                    </button>
                 </div>
              </div>
              <!-- 关节 5 -->
              <div class="flex flex-col items-center gap-3">
                 <span class="text-base font-bold text-zinc-200">手腕俯仰</span>
                 <div class="bg-black/30 rounded-2xl p-2 flex justify-center gap-2 border border-white/5">
                    <button class="force-animate-btn w-14 h-14" @mousedown="pressKey('l')" @mouseup="releaseKey('l')" @mouseleave="releaseKey('l')" :class="{ 'active': activeKeys.has('l') }">
                      <span class="text-2xl font-bold">↓</span>
                    </button>
                    <button class="force-animate-btn w-14 h-14" @mousedown="pressKey('j')" @mouseup="releaseKey('j')" @mouseleave="releaseKey('j')" :class="{ 'active': activeKeys.has('j') }">
                      <span class="text-2xl font-bold">↑</span>
                    </button>
                 </div>
              </div>
          </div>

          <!-- Section 4: 急停滑块(居中) -->
          <div class="flex items-center justify-center gap-6 pl-10 xl:border-l border-white/5 shrink-0">
             <!-- 紧急停止滑块 -->
             <div class="flex flex-col items-center gap-2">
               <div class="relative w-80 h-24 bg-red-900/20 rounded-full border-2 border-red-500/30 overflow-hidden select-none"
                    :class="{ 'border-red-500 ring-4 ring-red-500/20': isSliding }">
                 
                  <!-- 背景文字 -->
                  <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <span class="text-xl font-bold text-red-500/50 tracking-[0.3em] transition-opacity" :style="{ opacity: 1 - slideProgress }">滑动急停</span>
                  </div>
                 
                  <!-- 激活填充 -->
                  <div class="absolute inset-y-0 left-0 bg-red-500/20 transition-all duration-75 ease-linear" :style="{ width: (slideOffset + 44) + 'px' }"></div>

                  <!-- 滑块手柄 -->
                  <div class="absolute top-1 left-1 bottom-1 w-[88px] bg-red-500 rounded-full flex items-center justify-center shadow-[0_0_20px_rgba(239,68,68,0.5)] cursor-grab active:cursor-grabbing hover:scale-105 transition-transform duration-100 z-10"
                       :style="{ transform: `translateX(${slideOffset}px)` }"
                       @mousedown="handleSlideStart">
                    <span class="material-symbols-outlined text-white text-4xl">power_settings_new</span>
                  </div>
               </div>
             </div>
          </div>
        </div>

      </div>
    </main>

    <!-- 右侧:语音和摄像头控制面板 -->
    <div class="fixed right-8 top-1/2 -translate-y-1/2 z-[100] pointer-events-none animate-[fadeInRight_1s_ease-out_0.5s_forwards]">
       <div class="glass-panel py-6 px-4 shadow-2xl pointer-events-auto flex flex-col items-center gap-6">
          <!-- 语音控制按钮 -->
          <div class="relative">
             <!-- 声波扩散动画层 (三层呼吸光晕) -->
             <div v-if="isListening" class="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div class="absolute w-20 h-20 rounded-2xl bg-primary/30 border-2 border-primary/40" style="animation: soundWave 2s ease-out infinite;"></div>
                <div class="absolute w-20 h-20 rounded-2xl bg-primary/25 border-2 border-primary/30" style="animation: soundWave 2s ease-out infinite 0.6s;"></div>
                <div class="absolute w-20 h-20 rounded-2xl bg-primary/20 border-2 border-primary/20" style="animation: soundWave 2s ease-out infinite 1.2s;"></div>
             </div>
             
             <!-- 按钮本体 -->
             <button class="relative w-20 h-20 rounded-2xl bg-zinc-800/20 hover:bg-zinc-800 border border-white/5 flex flex-col items-center justify-center transition-all duration-300 group hover:scale-110 active:scale-95 ease-[cubic-bezier(0.25,0.1,0.25,1)] z-10"
                @click="toggleVoice" :class="{ 'bg-primary/10 border-primary/40 shadow-[0_0_30px_rgba(208,187,149,0.4)]': isListening }">
                <span class="material-symbols-outlined text-4xl transition-all" :class="isListening ? 'text-primary animate-pulse' : 'text-zinc-500 group-hover:text-white'">mic</span>
             </button>
          </div>

          <!-- 摄像头按钮 -->
          <div class="relative">
             <button class="relative w-20 h-20 rounded-2xl bg-zinc-800/20 hover:bg-zinc-800 border border-white/5 flex flex-col items-center justify-center transition-all duration-300 group hover:scale-110 active:scale-95 ease-[cubic-bezier(0.25,0.1,0.25,1)] z-10"
                @click="showCamera = !showCamera" :class="{ 'bg-emerald-500/10 border-emerald-500/40 shadow-[0_0_30px_rgba(16,185,129,0.2)]': showCamera }">
                <span class="material-symbols-outlined text-4xl transition-all" :class="showCamera ? 'text-emerald-400' : 'text-zinc-500 group-hover:text-white'">videocam</span>
             </button>
          </div>
       </div>
    </div>

    <!-- 键盘快捷键提示 -->
    <Transition name="ios-pop">
      <div v-if="showKeyHints" class="fixed top-24 right-8 w-64 glass-panel-hint p-6 shadow-2xl z-[60] origin-top-right">
          <h4 class="text-sm font-bold text-zinc-400 tracking-wide mb-4">键盘控制</h4>
          <div class="space-y-3">
            <div class="flex justify-between items-center text-sm" v-for="(label, keyPair) in hintMap" :key="keyPair">
               <span class="text-zinc-400 font-medium">{{ label }}</span>
               <div class="flex gap-1">
                  <span class="px-2 py-1 rounded-md bg-white/10 text-white font-mono text-xs min-w-[24px] text-center">{{ keyPair.split('/')[0] }}</span>
                  <span class="px-2 py-1 rounded-md bg-white/10 text-white font-mono text-xs min-w-[24px] text-center">{{ keyPair.split('/')[1] }}</span>
               </div>
            </div>
          </div>
      </div>
    </Transition>

    <!-- 摄像头画面弹窗 (悬浮组件) -->
    <Transition
      enter-active-class="transition-all duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)]"
      enter-from-class="opacity-0 scale-0 -translate-y-16 blur-md origin-top-right"
      enter-to-class="opacity-100 scale-100 translate-y-0 blur-0 origin-top-right"
      leave-active-class="transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]"
      leave-from-class="opacity-100 scale-100 translate-y-0 blur-0 origin-top-right"
      leave-to-class="opacity-0 scale-0 -translate-y-16 blur-md origin-top-right"
    >
      <CameraStream 
        v-if="showCamera" 
        ref="cameraStreamRef"
        :url="cameraUrl" 
        title="手机摄像头"
        @close="showCamera = false" 
        @calibration-click="handleCalibrationClick"
        @loaded="handleCameraLoaded"
      />
    </Transition>

    <Transition name="sim-panel-pop">
      <SimulationPanel v-if="showSimPanel" :anchor-rect="simPanelAnchor" @close="showSimPanel = false" />
    </Transition>

    <!-- 标定流程控制台 -->
    <Transition name="fade">
       <div v-if="showCamera && (tempCalibrationPoint || calibrationCount > 0)" class="fixed bottom-40 right-96 z-[60] flex items-end gap-4 animate-in slide-in-from-right-10 fade-in duration-500">
          
          <!-- 待确认的点 -->
          <div v-if="tempCalibrationPoint" class="bg-zinc-900/90 backdrop-blur-xl border border-primary/30 p-4 rounded-2xl shadow-2xl flex flex-col gap-3 min-w-[240px]">
             <div class="flex items-center gap-2 text-primary font-bold text-sm">
                <span class="material-symbols-outlined animate-bounce">touch_app</span>
                <span>确认标定点?</span>
             </div>
             <div class="text-xs text-zinc-400">
                1. 确保机械臂末端已移动到红点位置<br>
                2. 保持手机和物体静止
             </div>
             <div class="flex gap-2 mt-1">
                <button @click="saveCalibrationPoint" class="flex-1 bg-primary hover:bg-primary/90 text-black font-bold py-1.5 rounded-lg text-xs transition-colors">
                   记录当前位置
                </button>
                <button @click="tempCalibrationPoint = null" class="px-3 bg-white/10 hover:bg-white/20 text-white rounded-lg text-xs transition-colors">
                   取消
                </button>
             </div>
          </div>

          <!-- 标定状态面板 -->
          <div class="bg-zinc-900/80 backdrop-blur-md border border-white/10 p-4 rounded-2xl flex flex-col gap-3 min-w-[160px]">
             <div class="flex justify-between items-center border-b border-white/5 pb-2">
                <span class="text-xs font-bold text-zinc-300">标定进度</span>
                <span class="text-xs font-mono text-primary">{{ calibrationCount }} / 4</span>
             </div>
             
             <!-- 进度条 -->
             <div class="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
                <div class="h-full bg-primary transition-all duration-300 ease-out" :style="{ width: Math.min((calibrationCount / 4) * 100, 100) + '%' }"></div>
             </div>

             <div class="flex flex-col gap-2 mt-1">
                <button 
                  v-if="calibrationCount >= 4"
                  @click="runCalibration"
                  class="w-full bg-emerald-500 hover:bg-emerald-400 text-white font-bold py-1.5 rounded-lg text-xs shadow-lg shadow-emerald-500/20 transition-all active:scale-95"
                >
                   计算变换矩阵
                </button>
                <button @click="clearCalibration" class="w-full text-zinc-500 hover:text-white text-[10px] py-1 border border-transparent hover:border-white/10 rounded transition-colors">
                   清空数据
                </button>
             </div>
          </div>
       </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import RobotArm3D from './components/RobotArm3D.vue'
import DeepSeekPanel from './components/DeepSeekPanel.vue'

// --- State ---
import CameraStream from './components/CameraStream.vue'
import SimulationPanel from './components/SimulationPanel.vue'

// --- State ---
const connected = ref(false)
const isDemoMode = ref(false)
const activeKeys = reactive(new Set())
const logs = ref([])
const runningTime = ref('00:00:00')
const gripperOpen = ref(false)
const showKeyHints = ref(false)
const isShiftPressed = ref(false)
const drawerCollapsed = ref(false)
const isListening = ref(false)
const showSimPanel = ref(false)
const simPanelAnchor = ref(null)
const isTracking = ref(false)
const cameraStreamRef = ref(null)

// 控制mode状态: 'simulation' (仅 3D 模型) 或 'physical' (同时控制physical机械臂)
const controlMode = ref('simulation')
const isPhysicalAvailable = ref(false)


const GREETING_REGEX = /(你好|您好|hello|hi|嗨)/i
const GREETING_COOLDOWN_MS = 60 * 1000
const LOG_DUPLICATE_COOLDOWN_MS = 5 * 1000
let lastGreetingTimestamp = 0
let lastLogMessage = ''
let lastLogTimestamp = 0

// DeepSeek State
const deepSeekMessages = ref([
  { role: 'assistant', content: '你好!我是 Zero 机械臂助手,请问有什么可以帮您?', time: new Date().toLocaleTimeString() }
])
const isDeepSeekProcessing = ref(false)

async function runTestSequence() {
  addLog('>> Starting test sequence...', 'text-primary')
  
  const demoTargets = [
    { name: '复位姿态', position: { x: 0.18, y: 0.0, z: 0.30 } },
    { name: '左前方巡检', position: { x: 0.16, y: -0.12, z: 0.32 } },
    { name: '右前方巡检', position: { x: 0.16, y: 0.12, z: 0.32 } },
    { name: '高位巡视', position: { x: 0.10, y: 0.0, z: 0.36 } }
  ]

  for (let i = 0; i < demoTargets.length; i++) {
    const { name, position } = demoTargets[i]
    addLog('>> Demo ${i + 1}/${demoTargets.length}: ' + name, 'text-blue-300')
    await moveToTarget(position.x, position.y, position.z)
    // Small pause between moves
    await new Promise(r => setTimeout(r, 500))
  }
  
  addLog('[OK] Test sequence completed', 'text-emerald-400')
}

function toggleSimPanel(evt) {
  if (!showSimPanel.value) {
    const el = evt?.currentTarget
    if (el && typeof el.getBoundingClientRect === 'function') {
      const r = el.getBoundingClientRect()
      simPanelAnchor.value = {
        top: r.top,
        left: r.left,
        right: r.right,
        bottom: r.bottom,
        width: r.width,
        height: r.height
      }
    }
    showSimPanel.value = true
  } else {
    showSimPanel.value = false
  }
}

// 标定逻辑
const tempCalibrationPoint = ref(null)
const calibrationCount = ref(0)
const isCalibrating = ref(false)

// 摄像头状态
const showCamera = ref(false)
const cameraUrl = ref('http://localhost:5000/api/video_feed')

// 末端位置数据
// 末端位置数据
const endEffectorPos = ref({ x: '0.000', y: '0.000', z: '0.000' })
const targetEndEffectorPos = ref(null) // 新增:目标位置用于可视化 (红色幽灵点)

const targetAngles = ref([0, 0, 0, 0, 0, 0])      // 目标角度(指令)
const actualAngles = ref([0, 0, 0, 0, 0, 0])      // 真实角度(回读)
const displayAngles = ref([0, 0, 0, 0, 0, 0])     // 显示角度(平滑插值)

// 遥测状态
const errorCode = ref(0)
const isMockSignal = ref(true)
const lastTelemetryTime = ref(0)

const keyMap = {
  'a': { joint: 0, dir: -1 }, 'd': { joint: 0, dir: 1 },
  'w': { joint: 1, dir: -1 }, 's': { joint: 1, dir: 1 },
  'r': { joint: 2, dir: -1 }, 'f': { joint: 2, dir: 1 },
  'i': { joint: 3, dir: -1 }, 'k': { joint: 3, dir: 1 },
  'j': { joint: 4, dir: -1 }, 'l': { joint: 4, dir: 1 },
  'u': { joint: 5, dir: -1 }, 'o': { joint: 5, dir: 1 },
}

const hintMap = {
  'A/D': '基座旋转',
  'W/S': '大臂俯仰',
  'R/F': '从臂',
  'I/K': '手腕旋转',
  'J/L': '手腕俯仰',
  'U/O': '工具旋转'
}

let ws = null
let updateInterval = null
let animationFrame = null
let startTime = Date.now()
let retryCount = 0
const maxRetries = 3

// --- Logic ---
function animateAngles() {
  // 降低插值速度,实现更平滑的动画效果
  // 0.12 → 0.03 (降低到原来的 1/4,动画更缓慢)
  const lerp = 0.03
  const c = displayAngles.value, t = targetAngles.value
  for (let i = 0; i < 6; i++) c[i] += (t[i] - c[i]) * lerp
  displayAngles.value = [...c]
  animationFrame = requestAnimationFrame(animateAngles)
}

function connect() {
  addLog('System initializing...', 'text-zinc-500')
  
  // 使用 native WebSocket 连接 Python 后端
  ws = new WebSocket('ws://localhost:5000/ws/mujoco')
  
  ws.onopen = () => {
    connected.value = true
    isDemoMode.value = false
    retryCount = 0
    addLog('Ready: Backend connected (MuJoCo)', 'text-emerald-400')
    ws.send(JSON.stringify({ action: "start" }))
    
    // 同步控制mode
    syncControlMode()
    
    // 启动心跳 (每5秒发送一次Ping)
    if (window.wsHeartbeat) clearInterval(window.wsHeartbeat)
    window.wsHeartbeat = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: "ping" }))
        }
    }, 5000)
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'joint_update') {
         if (data.angles_rad) {
            displayAngles.value = data.angles_rad
         }
         if (data.ee_pos) {
            endEffectorPos.value = {
               x: data.ee_pos[0].toFixed(3),
               y: data.ee_pos[1].toFixed(3),
               z: data.ee_pos[2].toFixed(3)
            }
         }
      } else if (data.type === 'connected') {
         addLog('Connected to simulation', 'text-blue-400')
         // 更新控制mode
         if (data.control_mode) {
           controlMode.value = data.control_mode
         }
      } else if (data.type === 'dispatch_result') {
         // 处理指令分发结果
         if (data.mode === 'physical' && data.serial_sent) {
           addLog('>> 串口command sent (mock=' + data.serial_mock + ')', 'text-cyan-400')
         }
      } else if (data.type === 'mode_info') {
         controlMode.value = data.mode
         isPhysicalAvailable.value = data.serial_available
      } else if (data.type === 'telemetry') {
         // 处理遥测数据
         const telemetryData = data.data || data
         
         // 更新真实角度(度数转弧度)
         if (telemetryData.angles_deg) {
           actualAngles.value = telemetryData.angles_deg.map(deg => 
             deg !== null ? deg * Math.PI / 180 : 0
           )
         } else if (telemetryData.angles_rad) {
           actualAngles.value = telemetryData.angles_rad.map(rad => rad !== null ? rad : 0)
         }
         
         // 物理mode下,显示真实角度;Simulation Mode下继续显示目标角度
         if (controlMode.value === 'physical') {
           displayAngles.value = [...actualAngles.value]
         }
         
         // 更新错误码和simulation信号状态
         errorCode.value = telemetryData.error_code || 0
         isMockSignal.value = telemetryData.serial_mock !== false
         lastTelemetryTime.value = Date.now()
      }
    } catch (e) {
      console.error('WS Parse Error', e)
    }
  }


  ws.onclose = () => {
    connected.value = false
    addLog('Connection lost', 'text-red-400')
    if (retryCount < maxRetries) {
      retryCount++
      setTimeout(connect, 2000 * retryCount)
    } else {
      isDemoMode.value = true
      addLog('Mode: Offline demo', 'text-amber-500')
    }
  }

  ws.onerror = (err) => {
    console.error('WS Error', err)
    connected.value = false
  }
}

function handleTargetUpdate(e) {
  const d = e.detail
  if (d && typeof d.x === 'number') {
    targetEndEffectorPos.value = { x: d.x, y: d.y, z: d.z }
  }
}

onMounted(() => {
  window.addEventListener('target-update', handleTargetUpdate)
})

onUnmounted(() => {
  window.removeEventListener('target-update', handleTargetUpdate)
})
function sendCommand(cmd) {
  if (connected.value && ws && ws.readyState === WebSocket.OPEN) {
    // 转换格式适配 main.py
    if (cmd.type === 'move_to_angles') {
       ws.send(JSON.stringify({ 
         action: 'set_target', 
         target: targetEndEffectorPos.value ? [targetEndEffectorPos.value.x, targetEndEffectorPos.value.y, targetEndEffectorPos.value.z] : [0.1, -0.2, 0.3] 
       }))
    } else {
       ws.send(JSON.stringify(cmd))
    }
  }
}

function pressKey(key) {
  if (activeKeys.has(key)) return
  activeKeys.add(key)
  const baseSpeed = 2.5
  const speed = isShiftPressed.value ? baseSpeed * 2 : baseSpeed
  sendCommand({ type: 'keyboard', key, speed })
  if (!updateInterval) updateInterval = setInterval(updateAllJoints, 30)
}

function releaseKey(key) {
  if (!activeKeys.has(key)) return
  activeKeys.delete(key)
  sendCommand({ type: 'stop', key, speed: 0 })
  if (activeKeys.size === 0 && updateInterval) { clearInterval(updateInterval); updateInterval = null }
}

function updateAllJoints() {
  if (activeKeys.size === 0) return
  const baseStep = 0.01 
  const multiplier = isShiftPressed.value ? 2.5 : 1.0
  const step = baseStep * multiplier
  const angles = [...targetAngles.value]
  activeKeys.forEach(key => {
    const m = keyMap[key]
    if (m) angles[m.joint] += step * m.dir
  })
  targetAngles.value = angles
}

function resetRobot() {
  activeKeys.clear()
  if (updateInterval) { clearInterval(updateInterval); updateInterval = null }
  sendCommand({ type: 'reset' })
  targetAngles.value = [0, 0, 0, 0, 0, 0]
  addLog('Command: System reset', 'text-white')
}

// ========== 控制mode管理 ==========
async function syncControlMode() {
  try {
    const res = await fetch('http://localhost:5000/api/control/mode')
    const data = await res.json()
    controlMode.value = data.mode
    isPhysicalAvailable.value = data.serial_available
  } catch (e) {
    console.error('Failed to sync control mode', e)
  }
}

async function toggleControlMode() {
  const newMode = controlMode.value === 'simulation' ? 'physical' : 'simulation'
  try {
    const res = await fetch('http://localhost:5000/api/control/mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: newMode })
    })
    const data = await res.json()
    if (data.success) {
      controlMode.value = data.mode
      const modeLabel = data.mode === 'simulation' ? '>> Simulation Mode' : '>> Physical Mode'
      addLog('Switched to ' + modeLabel, 'text-primary')
    }
  } catch (e) {
    addLog('[X] Mode switch failed', 'text-red-400')
  }
}

// ========== 动作序列系统 ==========

const isPlayingSequence = ref(false)
const currentSequence = ref(null)

// 预定义动作库
const actionLibrary = {
  wave: {
    name: '挥手',
    keyframes: [
      { angles: [0, -30, 45, 0, -15, 0], duration: 1000 },     // 抬起手臂
      { angles: [15, -30, 45, 0, -15, 30], duration: 500 },   // 向右摆
      { angles: [-15, -30, 45, 0, -15, -30], duration: 500 }, // 向左摆
      { angles: [15, -30, 45, 0, -15, 30], duration: 500 },   // 再向右
      { angles: [0, 0, 0, 0, 0, 0], duration: 1000 }           // 归位
    ]
  },
  grab_demo: {
    name: '抓取Demo',
    keyframes: [
      { angles: [0, -20, 30, 0, -10, 0], duration: 1000 },     // 准备姿态
      { angles: [0, -45, 60, 0, -15, 0], duration: 800 },      // 俯身
      { angles: [0, -45, 60, 0, -15, 0], duration: 300, gripper: false }, // 夹紧
      { angles: [0, -20, 30, 0, -10, 0], duration: 800 },      // 抬起
      { angles: [45, -20, 30, 0, -10, 45], duration: 1000 },   // 转向
      { angles: [45, -45, 60, 0, -15, 45], duration: 800 },    // 放下
      { angles: [45, -45, 60, 0, -15, 45], duration: 300, gripper: true }, // 松开
      { angles: [0, 0, 0, 0, 0, 0], duration: 1200 }            // 归位
    ]
  },
  dance: {
    name: '小舞',
    keyframes: [
      { angles: [0, -30, 30, 0, 0, 0], duration: 500 },
      { angles: [30, -30, 30, 30, 0, 30], duration: 400 },
      { angles: [-30, -30, 30, -30, 0, -30], duration: 400 },
      { angles: [30, -30, 30, 30, 0, 30], duration: 400 },
      { angles: [0, 0, 60, 0, -60, 0], duration: 600 },
      { angles: [0, 0, 0, 0, 0, 0], duration: 800 }
    ]
  },
  spin: {
    name: '原地转圈',
    keyframes: [
      { angles: [179, 0, 0, 0, 0, 0], duration: 2000 },
      { angles: [-179, 0, 0, 0, 0, 0], duration: 4000 },
      { angles: [0, 0, 0, 0, 0, 0], duration: 2000 }
    ]
  },
  nod: {
    name: '点头',
    keyframes: [
      { angles: [0, 0, 0, 0, 30, 0], duration: 300 },
      { angles: [0, 0, 0, 0, -20, 0], duration: 300 },
      { angles: [0, 0, 0, 0, 30, 0], duration: 300 },
      { angles: [0, 0, 0, 0, 0, 0], duration: 300 }
    ]
  },
  greet: {
    name: '打招呼',
    keyframes: [
      { angles: [0, -40, 50, 0, -10, 0], duration: 800 },      // 抬手准备
      { angles: [0, -40, 50, 0, -10, 30], duration: 300 },     // 手掌转向
      { angles: [0, -40, 50, 0, -10, -30], duration: 300 },    // 摆动1
      { angles: [0, -40, 50, 0, -10, 30], duration: 300 },     // 摆动2
      { angles: [0, -40, 50, 0, -10, 0], duration: 300 },      // 停止
      { angles: [0, 0, 0, 0, 0, 0], duration: 1000 }            // 归位
    ]
  }
}

// 三次缓动函数 (ease-in-out)
function easeInOutCubic(t) {
  return t < 0.5 
    ? 4 * t * t * t 
    : 1 - Math.pow(-2 * t + 2, 3) / 2
}

/**
 * 快速碰撞检测 - 避免90%的穿模情况
 * @param {Object} angles - 关节角度(度数)
 * @returns {Boolean} true=有碰撞风险,false=安全
 */
const DEG2RAD = Math.PI / 180
const RAD2DEG = 180 / Math.PI

const JOINT_LIMITS_DEG = [
  { min: -170, max: 170 },  // Joint1 基座
  { min: -15, max: 135 },   // Joint2 大臂
  { min: 0, max: 140 },     // Joint3 小臂 - 禁止向后折
  { min: -90, max: 120 },   // Joint4 腕1 - 限制内旋
  { min: -95, max: 95 },    // Joint5 腕2
  { min: -180, max: 180 }   // Joint6 末端
]

const SHOULDER_ELBOW_MIN = -110
const SHOULDER_ELBOW_MAX = 160
const WRIST_COUPLED_LIMIT = 190
const ELBOW_FORWARD_MAX = 145
const LINK_LENGTHS_M = {
  baseHeight: 0.044,   // 基座到肩部轴心
  shoulder: 0.0215,    // 肩部短连杆(link1->link2)
  upperArm: 0.0827,    // 肩到肘(link2->link3)
  forearm: 0.0450,     // 肘到腕(link3->link4)
  wrist: 0.0392,       // 腕段(link4->link5)
  flange: 0.0540       // 腕到末端(link5->link6)
}
const BASE_RADIUS_M = 0.09
const BASE_CLEARANCE_M = 0.02

function clamp(value, min, max) {
  if (Number.isNaN(value)) return min
  return Math.min(Math.max(value, min), max)
}

function mapAnglesObjectToArray(angleObj) {
  return [
    angleObj?.joint1 ?? 0,
    angleObj?.joint2 ?? 0,
    angleObj?.joint3 ?? 0,
    angleObj?.joint4 ?? 0,
    angleObj?.joint5 ?? 0,
    angleObj?.joint6 ?? 0,
  ]
}

function mapAnglesArrayToObject(angleArray) {
  return {
    joint1: angleArray[0],
    joint2: angleArray[1],
    joint3: angleArray[2],
    joint4: angleArray[3],
    joint5: angleArray[4],
    joint6: angleArray[5],
  }
}

function enforceJointSafety(rawAnglesDeg) {
  const safe = rawAnglesDeg.map((deg, idx) => clamp(deg, JOINT_LIMITS_DEG[idx].min, JOINT_LIMITS_DEG[idx].max))

  // Shoulder + elbow coupling to avoid folding into pedestal
  const shoulderElbow = safe[1] + safe[2]
  if (shoulderElbow < SHOULDER_ELBOW_MIN) {
    safe[2] = clamp(SHOULDER_ELBOW_MIN - safe[1], JOINT_LIMITS_DEG[2].min, JOINT_LIMITS_DEG[2].max)
  } else if (shoulderElbow > SHOULDER_ELBOW_MAX) {
    safe[2] = clamp(SHOULDER_ELBOW_MAX - safe[1], JOINT_LIMITS_DEG[2].min, JOINT_LIMITS_DEG[2].max)
  }

  // Prevent elbow from exceeding forward reach (based on model interference)
  if (safe[2] > ELBOW_FORWARD_MAX) {
    safe[2] = ELBOW_FORWARD_MAX
  }

  // Wrist pitch + wrist bend combined envelope
  const wristCombined = Math.abs(safe[3]) + Math.abs(safe[4])
  if (wristCombined > WRIST_COUPLED_LIMIT) {
    const excess = wristCombined - WRIST_COUPLED_LIMIT
    const reduction = excess / 2
    safe[3] = clamp(safe[3] - Math.sign(safe[3]) * reduction, JOINT_LIMITS_DEG[3].min, JOINT_LIMITS_DEG[3].max)
    safe[4] = clamp(safe[4] - Math.sign(safe[4]) * reduction, JOINT_LIMITS_DEG[4].min, JOINT_LIMITS_DEG[4].max)
  }

  return safe
}

function getSafeAngles(angleObj, source = '指令') {
  const rawArray = mapAnglesObjectToArray(angleObj)
  const safeArray = enforceJointSafety(rawArray)
  const safeObj = mapAnglesArrayToObject(safeArray)

  if (quickCollisionCheck(safeObj)) {
    addLog('[!] ' + source + ' 超出安全范围,已取消执行', 'text-amber-400')
    return null
  }

  return {
    deg: safeObj,
    rad: safeArray.map(deg => deg * DEG2RAD)
  }
}

function computeForwardPositions(angles) {
  const baseYaw = (angles.joint1 || 0) * DEG2RAD
  const shoulder = (angles.joint2 || 0) * DEG2RAD
  const elbow = (angles.joint3 || 0) * DEG2RAD
  const wrist = (angles.joint4 || 0) * DEG2RAD

  const segmentLengths = [
    LINK_LENGTHS_M.shoulder + LINK_LENGTHS_M.upperArm,
    LINK_LENGTHS_M.forearm,
    LINK_LENGTHS_M.wrist + LINK_LENGTHS_M.flange
  ]
  const cumulativePitches = [
    shoulder,
    shoulder + elbow,
    shoulder + elbow + wrist
  ]
  const labels = ['肘部', '腕部', '末端']

  let results = []
  let radial = 0
  let height = LINK_LENGTHS_M.baseHeight

  for (let i = 0; i < segmentLengths.length; i++) {
    const len = segmentLengths[i]
    const pitch = cumulativePitches[i]

    radial += Math.sin(pitch) * len
    height += Math.cos(pitch) * len

    const x = radial * Math.cos(baseYaw)
    const y = radial * Math.sin(baseYaw)
    const r = Math.sqrt(x * x + y * y)

    results.push({
      label: labels[i],
      x,
      y,
      z: height,
      radial: r
    })
  }

  return results
}

function geometryCollisionCheck(angles) {
  const points = computeForwardPositions(angles)
  let risk = false
  const baseSafeHeight = LINK_LENGTHS_M.baseHeight + BASE_CLEARANCE_M

  points.forEach(point => {
    if (point.z < -0.005) {
      addLog('限制触发: ${point.label} 高度 ' + (point.z * 1000).toFixed(0) + 'mm 低于地面', 'text-amber-500')
      risk = true
    }

    if (point.z < baseSafeHeight && point.radial < BASE_RADIUS_M) {
      addLog('限制触发: ${point.label} 距基座 ${(point.radial * 1000).toFixed(0)}mm (< ' + (BASE_RADIUS_M * 1000).toFixed(0) + 'mm)', 'text-amber-500')
      risk = true
    }
  })

  return risk
}

function quickCollisionCheck(angles) {
  let risk = false

  Object.entries(angles).forEach(([key, value], idx) => {
    const limit = JOINT_LIMITS_DEG[idx]
    if (!limit) return
    if (value < limit.min || value > limit.max) {
      addLog('限制触发: ${key} ${value.toFixed(1)}° 超出 [${limit.min}, ' + limit.max + ']', 'text-amber-500')
      risk = true
    }
  })

  const sumShoulderElbow = angles.joint2 + angles.joint3
  if (sumShoulderElbow < SHOULDER_ELBOW_MIN) {
    addLog('限制触发: Joint2+Joint3 = ${sumShoulderElbow.toFixed(1)}° < ' + SHOULDER_ELBOW_MIN + '°', 'text-amber-500')
    risk = true
  }
  if (sumShoulderElbow > SHOULDER_ELBOW_MAX) {
    addLog('限制触发: Joint2+Joint3 = ${sumShoulderElbow.toFixed(1)}° > ' + SHOULDER_ELBOW_MAX + '°', 'text-amber-500')
    risk = true
  }

  if (angles.joint3 > ELBOW_FORWARD_MAX) {
    addLog('限制触发: Joint3 前探 ${angles.joint3.toFixed(1)}° > ' + ELBOW_FORWARD_MAX + '°', 'text-amber-500')
    risk = true
  }

  const wristCombined = Math.abs(angles.joint4) + Math.abs(angles.joint5)
  if (wristCombined > WRIST_COUPLED_LIMIT) {
    addLog('限制触发: 腕部组合角 ${wristCombined.toFixed(1)}° > ' + WRIST_COUPLED_LIMIT + '°', 'text-amber-500')
    risk = true
  }

  if (geometryCollisionCheck(angles)) {
    risk = true
  }

  return risk
}

// 播放动作序列
async function playActionSequence(sequenceOrName) {
  let sequence;
  if (typeof sequenceOrName === 'string') {
    sequence = actionLibrary[sequenceOrName];
  } else {
    sequence = sequenceOrName;
  }

  if (!sequence) {
    addLog('Unknown action: ' + sequenceOrName, 'text-red-400')
    return
  }

  if (isPlayingSequence.value) {
    addLog('动作序列进行中...', 'text-amber-400')
    return
  }

  isPlayingSequence.value = true
  currentSequence.value = sequenceName
  addLog('🎭 开始执行: ' + sequence.name, 'text-primary')

  try {
    for (let i = 0; i < sequence.keyframes.length; i++) {
      const keyframe = sequence.keyframes[i]
      const safe = getSafeAngles(mapAnglesArrayToObject(keyframe.angles), `动作关键帧 #${i+1}`)
      if (!safe) {
        isPlayingSequence.value = false
        currentSequence.value = null
        return
      }

      const startAngles = [...targetAngles.value]
      const endAngles = safe.rad
      const duration = keyframe.duration

      // 如果有夹爪控制
      if (keyframe.gripper !== undefined) {
        gripperOpen.value = keyframe.gripper
        addLog('夹爪: ' + keyframe.gripper ? '开启' : '关闭', 'text-zinc-400')
      }

      // 平滑插值
      const startTime = Date.now()
      await new Promise(resolve => {
        function animate() {
          const elapsed = Date.now() - startTime
          const progress = Math.min(elapsed / duration, 1)
          const easedProgress = easeInOutCubic(progress)

          // 插值计算
          const interpolatedAngles = startAngles.map((start, idx) => 
            start + (endAngles[idx] - start) * easedProgress
          )
          
          targetAngles.value = interpolatedAngles

          if (progress < 1) {
            animationFrame = requestAnimationFrame(animate)
          } else {
            resolve()
          }
        }
        animate()
      })

      // 关键帧之间的小停顿
      if (i < sequence.keyframes.length - 1) {
        await new Promise(r => setTimeout(r, 50))
      }
    }

    addLog('[OK] 动作完成: ' + sequence.name, 'text-emerald-400')
  } catch (error) {
    addLog('动作执行failed: ' + error.message, 'text-red-400')
  } finally {
    isPlayingSequence.value = false
    currentSequence.value = null
  }
}

// 停止当前动作序列
function stopActionSequence() {
  if (animationFrame) {
    cancelAnimationFrame(animationFrame)
    animationFrame = null
  }
  isPlayingSequence.value = false
  currentSequence.value = null
  addLog('动作序列已停止', 'text-amber-400')
}


// 跟踪逻辑
let trackingInterval = null

async function toggleTracking() {
  if (isTracking.value) {
    isTracking.value = false
    if (trackingInterval) {
      clearInterval(trackingInterval)
      trackingInterval = null
    }
    addLog('停止自动跟踪', 'text-zinc-400')
  } else {
    isTracking.value = true
    addLog('启动自动跟踪...', 'text-blue-400')
    trackingInterval = setInterval(runTrackingLoop, 500) // 2fps
  }
}

async function runTrackingLoop() {
  if (!isTracking.value || !cameraStreamRef.value) return

  try {
    const snapshot = await cameraStreamRef.value.captureSnapshot()
    if (!snapshot || !snapshot.blob) return

    const formData = new FormData()
    formData.append('file', snapshot.blob)

    // 1. Detect Object
    const detRes = await fetch('http://localhost:5000/api/detect', {
      method: 'POST',
      body: formData
    })
    const detData = await detRes.json()

    if (detData.success && detData.count > 0) {
      // Find object with highest confidence
      const target = detData.detections.sort((a, b) => b.confidence - a.confidence)[0]
      const { center_x, center_y } = target.bbox
      
      // Normalize coordinates
      const u = center_x / snapshot.width
      const v = center_y / snapshot.height
      
      // 2. Apply Calibration (u,v -> x,y,z)
      const calRes = await fetch('http://localhost:5000/api/calibration/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ u, v })
      })
      const calData = await calRes.json()
      
      if (calData.success) {
        const { x, y, z } = calData.position
        
        // 3. IK Calculate (x,y,z -> angles)
        // Add height offset (e.g. 10cm above object) if needed, or just go to target
        // Safe approach: Hover 5cm above
        const safeZ = z + 0.05
        
        const ikRes = await fetch('http://localhost:5000/api/ik/calculate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ x, y, z: safeZ })
        })
        const ikData = await ikRes.json()
        
        if (ikData.success) {
           const safe = getSafeAngles(ikData.angles, '自动跟踪IK')
           if (!safe) return

           targetAngles.value = safe.rad
           targetEndEffectorPos.value = { x, y, z: safeZ }
           
           if (connected.value) {
             sendCommand({ type: 'move_to_angles', angles: safe.rad })
           }
        }
      }
    }
  } catch (e) {
    console.error('Tracking loop error:', e)
  }
}

// 标定功能实现
const handleCameraLoaded = () => {
  addLog('摄像头已连接: 进入扫描待机姿态', 'text-blue-400')
  const scanPose = {
    joint1: 0,
    joint2: 0,
    joint3: -90,
    joint4: 0,
    joint5: 180,
    joint6: 0
  }
  
  // 1. 前端动画
  updateRobotJoints(scanPose, 3000)
  
  // 2. 发送给后端
  if (connected.value) {
    sendCommand({
      type: 'move_to_angles',
      angles: [0, 0, -90, 0, 180, 0],
      speed: 0.5
    })
  }
}

const handleCalibrationClick = (point) => {
    addLog('收到标点: u=${point.u.toFixed(2)}, v=' + point.v.toFixed(2), 'text-zinc-500')
    tempCalibrationPoint.value = point
}

const saveCalibrationPoint = async () => {
    if (!tempCalibrationPoint.value) return
    
    try {
        const { x, y, z } = endEffectorPos.value
        const payload = {
            u: tempCalibrationPoint.value.u,
            v: tempCalibrationPoint.value.v,
            x: parseFloat(x),
            y: parseFloat(y),
            z: parseFloat(z)
        }
        
        await fetch('http://localhost:5000/api/calibration/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        
        calibrationCount.value++
        tempCalibrationPoint.value = null 
        
        logs.value.unshift({ 
            time: new Date().toLocaleTimeString(), 
            message: `标定点 #${calibrationCount.value} 已记录`, 
            type: 'success' 
        })
    } catch (e) {
        console.error(e)
        logs.value.unshift({ time: new Date().toLocaleTimeString(), message: '标定记录failed', type: 'error' })
    }
}

// 标定函数已移至第1357行统一定义



const isSliding = ref(false)
const slideStartX = ref(0)
const slideOffset = ref(0)
const maxSlide = 180 // w-56 (224px) - w-14 (56px) - padding approx

const slideProgress = computed(() => Math.min(Math.max(slideOffset.value / maxSlide, 0), 1))

function handleSlideStart(e) {
  isSliding.value = true
  slideStartX.value = e.clientX
  // 添加全局事件监听,确保在任何地方松开鼠标都能停止滑动
  document.addEventListener('mousemove', handleSlideMove)
  document.addEventListener('mouseup', handleSlideEnd)
}

function handleSlideMove(e) {
  if (!isSliding.value) return
  const delta = e.clientX - slideStartX.value
  slideOffset.value = Math.max(0, Math.min(delta, maxSlide))
}

function handleSlideEnd() {
  if (!isSliding.value) return
  isSliding.value = false
  
  // 移除全局事件监听
  document.removeEventListener('mousemove', handleSlideMove)
  document.removeEventListener('mouseup', handleSlideEnd)
  
  if (slideOffset.value > maxSlide * 0.8) {
    emergencyStop()
  }
  // Spring back
  const interval = setInterval(() => {
    slideOffset.value *= 0.8
    if (slideOffset.value < 1) {
      slideOffset.value = 0
      clearInterval(interval)
    }
  }, 16)
}

function emergencyStop() {
  activeKeys.clear()
  resetRobot() 
  addLog('[!] 紧急停止触发 [!]', 'text-red-500 font-bold')
  // Haptic feedback if available?
}

function toggleGripper(isOpen) {
  gripperOpen.value = isOpen
  addLog('夹爪: ' + isOpen ? '开启' : '关闭' + '', 'text-zinc-400')
  
  // 发送Pump控制指令到后端
  fetch('http://localhost:5000/api/pump/control', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ state: isOpen })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      const mode = data.mock ? 'Mock' : 'Real'
      addLog('[OK] Pump command sent (' + mode + ')', 'text-emerald-400')
    } else {
      addLog('[X] Pump command failed: ' + (data.error || 'Unknown'), 'text-red-400')
    }
  })
  .catch(err => {
    console.error('Pump control failed:', err)
    addLog('[X] Pump control failed: ' + err.message, 'text-red-400')
  })
}

// Web Speech API 语音识别
let recognition = null;

function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    addLog('浏览器不支持语音识别', 'text-red-400');
    return;
  }

  recognition = new SpeechRecognition();
  recognition.lang = 'zh-CN';
  recognition.continuous = false;
  recognition.interimResults = false;

  recognition.onstart = () => {
    isListening.value = true;
    addLog('Listening...', 'text-primary');
  };

  recognition.onresult = async (event) => {
    const transcript = event.results[0][0].transcript;
    addLog('Recognized: ' + transcript, 'text-zinc-300');
    await processVoiceCommand(transcript);
  };

  recognition.onend = () => {
    isListening.value = false;
  };

  recognition.onerror = (event) => {
    isListening.value = false;
    if (event.error === 'no-speech') {
      addLog('No speech detected', 'text-amber-400');
    } else if (event.error === 'not-allowed') {
      addLog('Microphone access denied', 'text-red-400');
    } else {
      addLog('Recognition error: ' + event.error, 'text-red-400');
    }
  };
}

// 自动标定相关
const downloadAruco = () => {
    window.open('http://localhost:5000/api/calibration/aruco_marker', '_blank')
}

const autoDetectAruco = async () => {
    if (!cameraStreamRef.value) return
    
    addLog('正在自动搜索 ArUco 标记...', 'text-blue-400')
    const snapshot = await cameraStreamRef.value.captureSnapshot()
    if (!snapshot || !snapshot.blob) {
        addLog('[X] 截图失败', 'text-red-400')
        return
    }

    const formData = new FormData()
    formData.append('file', snapshot.blob)

    try {
        const res = await fetch('http://localhost:5000/api/calibration/auto_detect', {
            method: 'POST',
            body: formData
        })
        const data = await res.json()
        
        if (data.success) {
            addLog(`>> 检测到标记 (ID: ${data.id}) 位于 [${data.u.toFixed(2)}, ${data.v.toFixed(2)}]`, 'text-emerald-400')
            handleCalibrationClick({ u: data.u, v: data.v })
        } else {
            addLog('[!] 未能识别到标记: ' + (data.error || '可能是光线不足或距离太远'), 'text-amber-400')
        }
    } catch (e) {
        addLog('[X] 识别服务异常', 'text-red-400')
    }
}

async function processVoiceCommand(text) {
  try {
    // === 直接使用 LLM (DeepSeek) 进行全权处理 ===
    addLog('🤔 思考中...', 'text-zinc-500');
    
    try {
      const llmResponse = await fetch('http://localhost:5000/api/llm/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          current_pos: {
            x: parseFloat(endEffectorPos.value.x),
            y: parseFloat(endEffectorPos.value.y),
            z: parseFloat(endEffectorPos.value.z)
          },
          current_angles: displayAngles.value.map(a => parseFloat(a) * 180 / Math.PI)
        })
      });
      
      const llmResult = await llmResponse.json();
      
      if (llmResult.success) {
        // 1. 显示 LLM 回复
        if (llmResult.response) {
          addLog('>> ' + llmResult.response, 'text-blue-400');
          speak(llmResult.response);
        }
        
        // 2. 检查是否有附带的 IK 角度数据 (后端已计算)
        if (llmResult.angles) {
          const safe = getSafeAngles(llmResult.angles, 'LLM 指令')
          if (!safe) return false

          addLog('>> Executing LLM command...', 'text-primary')

          targetAngles.value = safe.rad

          if (connected.value) {
            sendCommand({
              type: 'move_to_angles',
              angles: targetAngles.value
            })
          }
        } 
        // 3. 检查是否是预定义动作序列 (如挥手)
        else if (llmResult.sequence) {
          // 高级权限:直接执行 LLM 生成的动态序列
          addLog('>> Executing sequence: ' + llmResult.sequence.name, 'text-purple-400');
          playActionSequence(llmResult.sequence);
        }
        else if (llmResult.action) {
          addLog('>> Action received: ' + llmResult.action, 'text-cyan-400');
          if (actionLibrary[llmResult.action]) {
            addLog('>> Playing action: ' + llmResult.action, 'text-emerald-400');
            playActionSequence(llmResult.action);
          } else if (llmResult.action === 'reset') {
            addLog('>> Executing reset', 'text-white');
            resetRobot();
          } else {
            addLog('[!] Unknown action: ' + llmResult.action + ',Available: wave/nod/spin/dance', 'text-amber-400');
          }
        }

        return true;
      } else {
        addLog('[!] ' + llmResult.error || 'Cannot process', 'text-amber-400');
        speak('Sorry, an error occurred');
        return false;
      }
    } catch (llmError) {
      console.error('LLM 调用failed:', llmError);
      addLog('[X] 大脑连接failed', 'text-red-400');
      speak('抱歉,大脑连接failed');
      return false;
    }
  } catch (e) {
    console.error('系统错误:', e);
    addLog('[X] 系统错误', 'text-red-400');
    speak('抱歉,系统发生错误');
    return false;
  }
}

function updateRobotJoints(angles, duration = 1500) {
  const safe = getSafeAngles(angles, '手动控制')
  if (!safe) return

  const goalAngles = safe.rad
  
  // [OK] 平滑轨迹插值 - 修复乱飞/穿模问题
  const startAngles = [...targetAngles.value]
  const startTime = Date.now()
  
  function interpolate() {
    const elapsed = Date.now() - startTime
    const progress = Math.min(elapsed / duration, 1)
    
    // 三次缓动函数(加速-减速)
    const eased = progress < 0.5
      ? 4 * progress * progress * progress
      : 1 - Math.pow(-2 * progress + 2, 3) / 2
    
    // 逐关节插值
    targetAngles.value = startAngles.map((start, i) =>
      start + (goalAngles[i] - start) * eased
    )
    
    if (progress < 1) {
      requestAnimationFrame(interpolate)
    } else {
      // 到达目标后发送后端指令
      if (connected.value) {
        sendCommand({
          type: 'move_to_angles',
          angles: goalAngles
        })
      }
    }
  }
  
  interpolate()
}

// ============================================================
// 笛卡尔路径规划 + 碰撞检测
// ============================================================

/**
 * 在3D空间中采样直线路径点
 */
function sampleLinePath(start, end, samples = 15) {
  const path = []
  for (let i = 0; i <= samples; i++) {
    const t = i / samples
    path.push({
      x: start.x + (end.x - start.x) * t,
      y: start.y + (end.y - start.y) * t,
      z: start.z + (end.z - start.z) * t
    })
  }
  return path
}

/**
 * 调用后端IK服务
 */
async function callIK(position) {
  try {
    const response = await fetch('http://localhost:5000/api/ik/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(position)
    })
    const result = await response.json()
    if (result.success) {
      const safeAngles = enforceJointSafety(mapAnglesObjectToArray(result.angles))
      return mapAnglesArrayToObject(safeAngles)
    } else {
      throw new Error(result.message || 'IK计算failed')
    }
  } catch (e) {
    console.error('IK调用failed:', e)
    throw e
  }
}

/**
 * 执行关节路径
 */
async function executeJointPath(jointPath, totalDuration = 2000) {
  if (jointPath.length === 0) return
  
  const startTime = Date.now()
  const pathLength = jointPath.length
  
  return new Promise((resolve) => {
    function animate() {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / totalDuration, 1)
      
      const segmentFloat = progress * (pathLength - 1)
      const segmentIndex = Math.floor(segmentFloat)
      const segmentProgress = segmentFloat - segmentIndex
      
      if (segmentIndex >= pathLength - 1) {
        const finalAngles = jointPath[pathLength - 1]
        targetAngles.value = [
          finalAngles.joint1 * Math.PI / 180,
          finalAngles.joint2 * Math.PI / 180,
          finalAngles.joint3 * Math.PI / 180,
          finalAngles.joint4 * Math.PI / 180,
          finalAngles.joint5 * Math.PI / 180,
          finalAngles.joint6 * Math.PI / 180
        ]
        resolve()
        return
      }
      
      const p1 = jointPath[segmentIndex]
      const p2 = jointPath[segmentIndex + 1]
      
      targetAngles.value = [
        (p1.joint1 + (p2.joint1 - p1.joint1) * segmentProgress) * Math.PI / 180,
        (p1.joint2 + (p2.joint2 - p1.joint2) * segmentProgress) * Math.PI / 180,
        (p1.joint3 + (p2.joint3 - p1.joint3) * segmentProgress) * Math.PI / 180,
        (p1.joint4 + (p2.joint4 - p1.joint4) * segmentProgress) * Math.PI / 180,
        (p1.joint5 + (p2.joint5 - p1.joint5) * segmentProgress) * Math.PI / 180,
        (p1.joint6 + (p2.joint6 - p1.joint6) * segmentProgress) * Math.PI / 180
      ]
      
      requestAnimationFrame(animate)
    }
    animate()
  })
}

/**
 * 移动到目标位置(带碰撞检测)
 */
async function moveToTarget(x, y, z, samples = 15) {
  try {
    addLog('规划路径: 目标(${x.toFixed(3)}, ${y.toFixed(3)}, ' + z.toFixed(3) + ')', 'text-blue-400')
    
    const currentPos = {
      x: parseFloat(endEffectorPos.value.x),
      y: parseFloat(endEffectorPos.value.y),
      z: parseFloat(endEffectorPos.value.z)
    }
    
    const path3D = sampleLinePath(currentPos, { x, y, z }, samples)
    addLog('生成' + path3D.length + '个路径点', 'text-zinc-500')
    
    const jointPath = []
    let collisionDetected = false
    
    for (let i = 0; i < path3D.length; i++) {
      const point = path3D[i]
      try {
        const safeAngles = await callIK(point)

        if (quickCollisionCheck(safeAngles)) {
          addLog('[!] 路径点' + i + '存在碰撞风险,取消移动', 'text-amber-400')
          collisionDetected = true
          break
        }

        jointPath.push(safeAngles)
      } catch (e) {
        addLog('路径点${i}IKfailed: ' + e.message, 'text-red-400')
        return
      }
    }
    
    if (collisionDetected) {
      return
    }
    
    addLog('IK计算完成,开始执行...', 'text-emerald-400')
    
    targetEndEffectorPos.value = { x, y, z }
    
    await executeJointPath(jointPath, 2000)
    
    addLog('[OK] 到达目标位置', 'text-emerald-400')
    
    if (connected.value) {
      sendCommand({
        type: 'move_to_position',
        position: { x, y, z }
      })
    }
  } catch (error) {
    addLog('路径规划failed: ' + error.message, 'text-red-400')
  }
}

// ============================================================


let currentAudio = null

async function speak(text) {
  // 1. 停止之前的播放
  if (currentAudio) {
    currentAudio.pause()
    currentAudio = null
  }
  window.speechSynthesis.cancel()

  // 2. 尝试调用后端 TTS (使用优化后的本地引擎)
  try {
    const response = await fetch('http://localhost:5000/api/tts/speak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        message: text,
        engine: 'local', // 切换回本地引擎,但后端已优化为 pyttsx3 (低延迟)
        voice: 'zh-CN-XiaoxiaoNeural'
      })
    })

    if (response.ok) {
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      currentAudio = new Audio(url)
      
      // 播放结束后清理资源
      currentAudio.onended = () => {
        URL.revokeObjectURL(url)
        currentAudio = null
      }
      
      await currentAudio.play()
      return // 成功播放,直接返回
    }
  } catch (e) {
    console.warn('后端 TTS 调用failed,降级为本地语音:', e)
  }

  // 3. 降级方案: 浏览器原生 Web Speech API
  const synthesis = window.speechSynthesis
  if (synthesis) {
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'zh-CN'
    utterance.rate = 1.0 // 稍微调快一点
    utterance.pitch = 1.0
    
    // 尝试选择更好的本地语音 (如 Google 或 Microsoft)
    const voices = synthesis.getVoices()
    const betterVoice = voices.find(v => v.name.includes('Google') || v.name.includes('Microsoft'))
    if (betterVoice) {
      utterance.voice = betterVoice
    }
    
    synthesis.speak(utterance)
  }
}

function toggleVoice() {
  if (!recognition) {
    initSpeechRecognition();
  }
  
  if (!recognition) {
    addLog('语音识别不可用', 'text-red-400');
    return;
  }
  
  if (isListening.value) {
    recognition.stop();
    isListening.value = false;
    addLog('停止聆听', 'text-zinc-400');
  } else {
    recognition.start();
  }
}

// 处理语音指令(从 VoiceControl 组件接收)
async function handleVoiceCommand(command) {
  console.log('收到语音指令:', command)
  addLog('语音指令: ' + JSON.stringify(command), 'text-primary')

  const text = command.message || command
  const isAngleCommand = /[0-9０-９]/.test(text) || text.includes('度') || text.includes('角度')

  if (isAngleCommand) {
    addLog('>> 解析角度类指令,交由 LLM 处理', 'text-primary')
    await processVoiceCommand(text)
    return
  }

  // 普通指令优先交给 LLM
  const handledByLLM = await processVoiceCommand(text)
  if (handledByLLM) return

  const allowPresetFallback = /(?:去|往|向|移动|到)?(左|右|前|后|上|下|高|低|中|中心|中间|初始|复位|归位|home|reset|拿|抓|捡)/i.test(text) && !/[0-9０-９度角]/.test(text)

  if (!allowPresetFallback) {
    addLog('[!] 指令暂未识别,暂不执行动作', 'text-amber-400')
    return
  }

  addLog('🧭 LLM 未解析成功,尝试调用预设动作(请确认安全)', 'text-amber-300')

  // 调用 IK 接口解析指令
  try {
    const response = await fetch('http://localhost:5000/api/ik/voice', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: text })
    })
    
    const result = await response.json()
    
    if (result.success) {
      const safe = getSafeAngles(result.angles, '预设动作')
      if (!safe) return

      targetAngles.value = safe.rad
      
      const preset = result.preset || '目标位置'
      addLog('移动到: ' + preset, 'text-emerald-400')
      
      // 发送到后端(如果连接)
      if (connected.value) {
        sendCommand({
          type: 'move_to_angles',
          angles: safe.rad
        })
      }
    } else {
      if (result.is_greeting) {
        addLog(result.message || '您好!', 'text-blue-400')
      } else {
        addLog('IK 错误: ' + result.message, 'text-red-400')
      }
    }
  } catch (e) {
    console.error('IK 调用failed:', e)
    addLog('IK 服务连接failed', 'text-red-400')
  }
}

// ============================================================
// 手眼标定功能
// ============================================================

async function runCalibration() {
  try {
    addLog('计算标定矩阵...', 'text-blue-400')
    
    const response = await fetch('http://localhost:5000/api/calibration/calculate', {
      method: 'POST'
    })
    
    const result = await response.json()
    
    if (result.success) {
      addLog('[OK] Calibration done!', 'text-emerald-400')
      addLog('误差: ' + result.error?.toFixed(4), 'text-zinc-400')
    } else {
      addLog('[X] 标定failed: ' + result.error, 'text-red-400')
    }
  } catch (e) {
    addLog('标定服务连接failed', 'text-red-400')
  }
}

async function clearCalibration() {
  try {
    const response = await fetch('http://localhost:5000/api/calibration/clear', {
      method: 'POST'
    })
    
    const result = await response.json()
    
    if (result.success) {
      calibrationCount.value = 0
      tempCalibrationPoint.value = null
      addLog('标定数据已清空', 'text-zinc-400')
    }
  } catch (e) {
    addLog('清空failed', 'text-red-400')
  }
}

async function addCalibrationPoint(pixelX, pixelY) {
  try {
    const currentPos = {
      x: parseFloat(endEffectorPos.value.x),
      y: parseFloat(endEffectorPos.value.y),
      z: parseFloat(endEffectorPos.value.z)
    }
    
    const response = await fetch('http://localhost:5000/api/calibration/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        u: pixelX,
        v: pixelY,
        ...currentPos
      })
    })
    
    const result = await response.json()
    
    if (result.success) {
      calibrationCount.value++
      addLog('添加标定点 ' + calibrationCount.value + '/4', 'text-emerald-400')
    } else {
      addLog('添加failed: ' + result.error, 'text-red-400')
    }
  } catch (e) {
    addLog('标定服务连接failed', 'text-red-400')
  }
}

// ============================================================


function handleChatResponse(data) {
  addLog('AI: ' + data.text, 'text-blue-400')
  if (data.action) {
    addLog('执行动作: ' + data.action, 'text-purple-400')
  }
}

function addLog(msg, color) {
  const now = Date.now()

  if (GREETING_REGEX.test(msg)) {
    if (now - lastGreetingTimestamp < GREETING_COOLDOWN_MS) {
      return
    }
    lastGreetingTimestamp = now
  }

  if (msg === lastLogMessage && (now - lastLogTimestamp) < LOG_DUPLICATE_COOLDOWN_MS) {
    return
  }

  lastLogMessage = msg
  lastLogTimestamp = now

  const time = new Date(now).toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
  logs.value.unshift({ time, message: msg, color })
  if (logs.value.length > 50) logs.value.pop()
}

function handleKeyDown(e) {
  if (e.key === 'Shift') { isShiftPressed.value = true; return }
  const k = e.key.toLowerCase()
  if (keyMap[k]) { e.preventDefault(); pressKey(k) }
  // Space 键改为语音控制(避免误触发紧急停止)
  if (e.code === 'Space') { e.preventDefault(); toggleVoice() } 
}

function handleKeyUp(e) {
  if (e.key === 'Shift') { isShiftPressed.value = false; return }
  const k = e.key.toLowerCase()
  if (keyMap[k]) { e.preventDefault(); releaseKey(k) }
}

async function handleDeepSeekSend(text) {
  // 1. Add User Message
  deepSeekMessages.value.push({
    role: 'user',
    content: text,
    time: new Date().toLocaleTimeString()
  })
  
  isDeepSeekProcessing.value = true
  
  // 2. Add placeholder for response
  const responseMsg = {
    role: 'assistant',
    content: '思考中...',
    time: new Date().toLocaleTimeString(),
    isThinking: true
  }
  deepSeekMessages.value.push(responseMsg)
  
  try {
    // 优先尝试 IK 指令
    const response = await fetch('http://localhost:5000/api/ik/voice', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: text })
    });
    
    const result = await response.json();
    
    if (result.success) {
      // IK 指令执行成功
      const preset = result.preset || '目标位置';
      responseMsg.content = `正在移动到: ${preset}`;
      responseMsg.isThinking = false;
      
      const angles = result.angles;
      targetAngles.value = [
        angles.joint1 * Math.PI / 180,
        angles.joint2 * Math.PI / 180,
        angles.joint3 * Math.PI / 180,
        angles.joint4 * Math.PI / 180,
        angles.joint5 * Math.PI / 180,
        angles.joint6 * Math.PI / 180
      ];
      
      if (connected.value) {
        sendCommand({ type: 'move_to_angles', angles: targetAngles.value });
      }
    } else {
      // 转发给 LLM
      if (result.is_greeting) {
        responseMsg.content = result.message;
        responseMsg.isThinking = false;
      } else {
        const llmResponse = await fetch('http://localhost:5000/api/llm/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            message: text,
            current_pos: {
              x: parseFloat(endEffectorPos.value.x),
              y: parseFloat(endEffectorPos.value.y),
              z: parseFloat(endEffectorPos.value.z)
            },
            current_angles: displayAngles.value.map(a => parseFloat(a) * 180 / Math.PI)
          })
        });
        
        const llmResult = await llmResponse.json();
        
        if (llmResult.success) {
          responseMsg.content = llmResult.response;
          responseMsg.isThinking = false;
          
          // 处理 Skills 返回的关节角度
          if (llmResult.angles) {
            const angles = llmResult.angles;
            addLog('>> 执行技能: ' + llmResult.action || 'control', 'text-primary');
            targetAngles.value = [
              angles.joint1 * Math.PI / 180,
              angles.joint2 * Math.PI / 180,
              angles.joint3 * Math.PI / 180,
              angles.joint4 * Math.PI / 180,
              angles.joint5 * Math.PI / 180,
              angles.joint6 * Math.PI / 180
            ];
            if (connected.value) {
              sendCommand({ type: 'move_to_angles', angles: targetAngles.value });
            }
          } else if (llmResult.sequence) {
            playActionSequence(llmResult.sequence);
          } else if (llmResult.action) {
            if (actionLibrary[llmResult.action]) {
              playActionSequence(llmResult.action);
            } else if (llmResult.action === 'reset') {
              resetRobot();
            }
          }
        } else {
          // 显示具体错误信息以便调试
          responseMsg.content = llmResult.error ? `(Error) ${llmResult.error}` : '抱歉,我没听懂您的指令';
          responseMsg.isThinking = false;
        }
      }
    }
  } catch (e) {
    console.error(e);
    responseMsg.content = '系统连接failed';
    responseMsg.isThinking = false;
  } finally {
    isDeepSeekProcessing.value = false;
  }
}

onMounted(() => {
  connect()
  animateAngles()
  window.addEventListener('keydown', handleKeyDown)
  window.addEventListener('keyup', handleKeyUp)
  
  // 暴露给控制台测试
  window.moveToTarget = moveToTarget
  window.runCalibration = runCalibration
  window.addCalibrationPoint = addCalibrationPoint
  window.clearCalibration = clearCalibration
  window.updateRobotJoints = updateRobotJoints // [OK] 新增暴露
  window.addEventListener('keyup', handleKeyUp)
  setInterval(() => {
    const e = Date.now() - startTime
    runningTime.value = new Date(e).toISOString().substr(11, 8)
  }, 1000)
})

onUnmounted(() => {
  if (ws) ws.close()
  if (updateInterval) clearInterval(updateInterval)
  cancelAnimationFrame(animationFrame)
  window.removeEventListener('keydown', handleKeyDown)
  window.removeEventListener('keyup', handleKeyUp)
  // 清理滑动事件监听
  document.removeEventListener('mousemove', handleSlideMove)
  document.removeEventListener('mouseup', handleSlideEnd)
})
</script>

<style>
/* Global Animations - Non-scoped to ensure Tailwind animate-[] works */
@keyframes slideDown {
  from { transform: translateY(-100%); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
@keyframes slideUp {
  from { transform: translateY(100%); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
@keyframes fadeInLeft {
  from { transform: translateX(-50px); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
/* 声波扩散动画 */
@keyframes soundWave {
  0% {
    transform: scale(1);
    opacity: 0.6;
  }
  50% {
    opacity: 0.3;
  }
  100% {
    transform: scale(2.5);
    opacity: 0;
  }
}
/* iOS Pop Animation */
.ios-pop-enter-active,
.ios-pop-leave-active {
  transition: opacity 0.3s, transform 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
}
.ios-pop-enter-from,
.ios-pop-leave-to {
  opacity: 0;
  transform: scale(0.8) translateY(-10px);
}

.sim-panel-pop-enter-active {
  animation: simPanelPopIn 560ms cubic-bezier(0.16, 1, 0.3, 1) both;
  will-change: transform, opacity, filter;
}
.sim-panel-pop-leave-active {
  animation: simPanelPopOut 300ms cubic-bezier(0.22, 1, 0.36, 1) both;
  will-change: transform, opacity, filter;
}
@keyframes simPanelPopIn {
  0% {
    opacity: 0;
    transform: translate3d(0, -10px, 0) scale(0.72);
    filter: blur(10px);
  }
  60% {
    opacity: 1;
    transform: translate3d(0, 0, 0) scale(1.02);
    filter: blur(0);
  }
  100% {
    opacity: 1;
    transform: translate3d(0, 0, 0) scale(1);
    filter: blur(0);
  }
}
@keyframes simPanelPopOut {
  0% {
    opacity: 1;
    transform: translate3d(0, 0, 0) scale(1);
    filter: blur(0);
  }
  100% {
    opacity: 0;
    transform: translate3d(0, -6px, 0) scale(0.92);
    filter: blur(8px);
  }
}

/* Global Button Styles to Ensure Hover Works */
.control-btn {
  @apply w-10 h-10 rounded-xl bg-zinc-800 hover:bg-zinc-700 active:scale-95 flex items-center justify-center text-zinc-400 hover:text-white transition-all duration-300 shadow-sm border border-white/5 hover:scale-125 hover:border-white/30 hover:shadow-[0_0_10px_rgba(255,255,255,0.1)] relative z-10 ease-[cubic-bezier(0.25,0.1,0.25,1)];
}
.control-btn.active {
  @apply bg-primary text-black border-primary shadow-[0_0_15px_rgba(208,187,149,0.3)] scale-95;
}

/* Glassmorphism Effect - 毛玻璃效果 */
.glass-panel {
  background: rgba(18, 18, 18, 0.15); /* 深色半透明背景 */
  backdrop-filter: blur(20px) saturate(180%); /* 背景模糊 + 饱和度增强 */
  -webkit-backdrop-filter: blur(20px) saturate(180%); /* Safari 兼容 */
  border: 1px solid rgba(255, 255, 255, 0.1); /* 半透明白色边框 */
  border-radius: 2.5rem; /* 圆角 */
  box-shadow: 
    0 8px 32px 0 rgba(0, 0, 0, 0.37), /* 外阴影 */
    inset 0 1px 0 0 rgba(255, 255, 255, 0.05); /* 内发光(顶部高光) */
}

/* 顶部导航栏毛玻璃 */
.glass-panel-header {
  background: rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(25px) saturate(180%);
  -webkit-backdrop-filter: blur(25px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 9999px; /* 完全圆角 */
  box-shadow: 
    0 8px 32px 0 rgba(0, 0, 0, 0.4),
    inset 0 1px 0 0 rgba(255, 255, 255, 0.08);
}

/* 系统日志毛玻璃 */
.glass-panel-log {
  background: linear-gradient(135deg, rgba(18, 18, 18, 0.2) 0%, rgba(0, 0, 0, 0.15) 100%);
  backdrop-filter: blur(25px) saturate(180%);
  -webkit-backdrop-filter: blur(25px) saturate(180%);
  border: 1px solid rgba(208, 187, 149, 0.15); /* 黄色主题边框 */
  border-radius: 1.5rem;
  box-shadow: 
    0 8px 32px 0 rgba(0, 0, 0, 0.4),
    inset 0 1px 0 0 rgba(208, 187, 149, 0.1); /* 黄色内发光 */
}

/* 键盘提示毛玻璃 */
.glass-panel-hint {
  background: rgba(0, 0, 0, 0.25);
  backdrop-filter: blur(30px) saturate(180%);
  -webkit-backdrop-filter: blur(30px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 1.5rem;
  box-shadow: 
    0 8px 32px 0 rgba(0, 0, 0, 0.5),
    inset 0 1px 0 0 rgba(255, 255, 255, 0.1);
}

.mini-btn {
  @apply w-8 h-8 rounded-lg hover:bg-white/10 flex items-center justify-center text-zinc-400 hover:text-white transition-transform duration-300 text-xs font-mono;
}

/* Pure CSS Force to bypass Tailwind JIT issues */
.force-animate-btn {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a1a1aa; /* zinc-400 */
  background-color: transparent;
  transition: all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1);
  cursor: pointer;
  position: relative;
  z-index: 20; /* Force above others */
}
.force-animate-btn:hover {
  background-color: rgba(255, 255, 255, 0.1) !important;
  color: white !important;
  transform: scale(1.15) !important;
  box-shadow: 0 0 15px rgba(255, 255, 255, 0.2) !important;
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
}
.force-animate-btn:active {
  transform: scale(0.95) !important;
  color: #d0bb95 !important; /* primary 黄色 */
  background-color: rgba(208, 187, 149, 0.1) !important;
}
.force-animate-btn.active {
   color: #d0bb95; /* primary 黄色 */
   background-color: rgba(208, 187, 149, 0.1);
   border: 1px solid rgba(208, 187, 149, 0.3);
   box-shadow: 0 0 15px rgba(208, 187, 149, 0.3);
}

@media (max-width: 640px) {
  .force-animate-btn:hover {
    transform: scale(1.08) !important;
  }
}
.mini-btn.active {
  @apply text-primary bg-primary/10;
}
</style>

<style scoped>
@keyframes pulse-dot {
  0% { opacity: 0.4; }
  50% { opacity: 0.8; }
  100% { opacity: 0.4; }
}
/* Log Mask Enhancement - Less Aggressive */
.mask-log-content {
  mask-image: linear-gradient(to bottom, black 90%, transparent 100%);
  -webkit-mask-image: linear-gradient(to bottom, black 90%, transparent 100%);
}

/* Custom Scrollbar for Log - Synced with DeepSeekPanel */
.scrollbar-thin {
  scrollbar-width: thin;
  scrollbar-color: rgba(208, 187, 149, 0.3) transparent;
}
.scrollbar-thin::-webkit-scrollbar {
  width: 4px;
  background-color: transparent;
}
.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}
.scrollbar-thin::-webkit-scrollbar-thumb {
  background-color: rgba(208, 187, 149, 0.3);
  border-radius: 10px;
  border: 1px solid transparent;
  background-clip: content-box;
  transition: all 0.3s ease;
}
.scrollbar-thin::-webkit-scrollbar-thumb:hover {
  background-color: rgba(208, 187, 149, 0.8);
  border: 0px solid transparent;
}
.scrollbar-track-transparent::-webkit-scrollbar-track {
  background: transparent;
}
.scrollbar-thumb-primary\/30::-webkit-scrollbar-thumb {
  background: rgba(208, 187, 149, 0.3);
}
.scrollbar-thumb-primary\/50:hover::-webkit-scrollbar-thumb {
  background: rgba(208, 187, 149, 0.5);
}

.bg-tech-grid {
    background-color: #000000;
    
    background-image: 
        /* 1. 中心核心辉光 (Brighter, Lower Saturation Cyan) */
        radial-gradient(circle at center, rgba(94, 210, 200, 0.2) 0%, transparent 45%),
        /* 2. 正方形网格线 */
        linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px),
        /* 3. 荧光点阵 */
        radial-gradient(circle, rgba(94, 210, 200, 0.5) 1px, transparent 1px);
    
    /* Grid 40px - High Density */
    background-size: 100% 100%, 40px 40px, 40px 40px, 80px 80px;
    background-repeat: no-repeat, repeat, repeat, repeat;
    background-position: center;
    background-blend-mode: screen;
    
    /* 呼吸动画 (Enhanced) */
    animation: pulse-dot 5s infinite ease-in-out;
    
    mask-image: radial-gradient(circle at center, black 0%, rgba(0,0,0,0.5) 50%, transparent 85%);
    -webkit-mask-image: radial-gradient(circle at center, black 0%, rgba(0,0,0,0.5) 50%, transparent 85%);
}
.mask-radial {
  mask-image: radial-gradient(circle at center, black 40%, transparent 80%);
  -webkit-mask-image: radial-gradient(circle at center, black 40%, transparent 80%);
}
.mask-gradient-bottom {
   mask-image: linear-gradient(to bottom, black 80%, transparent 100%);
   -webkit-mask-image: linear-gradient(to bottom, black 80%, transparent 100%);
}
.crosshair-glow {
    filter: drop-shadow(0 0 15px rgba(94, 210, 200, 0.9));
}
</style>
