<template>
  <div class="glass-panel-log p-6 shrink-0 pointer-events-auto flex flex-col transition-all duration-500 ease-[cubic-bezier(0.32,0.72,0,1)]"
       :class="isCollapsed ? 'h-[88px]' : 'flex-1 min-h-0'">
    
    <!-- Header -->
    <div @click="toggleCollapse" class="flex items-center justify-between cursor-pointer group hover:bg-white/5 -m-2 p-2 rounded-xl transition-all duration-300 mb-2">
      <div class="flex items-center gap-3">
        <span class="material-symbols-outlined text-primary text-xl animate-pulse">psychology</span>
        <h2 class="text-lg font-bold tracking-wide text-white group-hover:text-primary transition-colors">DEEPSEEK AI</h2>
      </div>
      <div class="w-7 h-7 rounded-full bg-white/5 flex items-center justify-center group-hover:bg-white/10 transition-colors">
        <span class="material-symbols-outlined text-zinc-500 group-hover:text-primary text-base transform transition-transform duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)]" 
              :class="{ 'rotate-180': !isCollapsed }">expand_more</span>
      </div>
    </div>

    <!-- Content Area -->
    <div class="flex-1 flex flex-col min-h-0 transition-opacity duration-300 delay-100"
         :class="isCollapsed ? 'opacity-0 invisible' : 'opacity-100 visible'">
      
      <!-- Chat History -->
      <div ref="chatContainer" class="flex-1 overflow-y-auto overflow-x-hidden space-y-3 pr-2 mb-4 mask-log-content font-sans text-sm leading-relaxed custom-scrollbar">
        <div v-for="(msg, index) in messages" :key="index" 
             class="flex flex-col gap-1 animate-in slide-in-from-left-2 fade-in duration-300">
          
          <!-- User Message -->
          <div v-if="msg.role === 'user'" class="self-end max-w-[90%] flex flex-col items-end">
            <div class="bg-primary/10 border border-primary/20 text-zinc-100 px-3 py-2 rounded-2xl rounded-tr-none font-medium tracking-wide break-all whitespace-pre-wrap">
              {{ msg.content }}
            </div>
            <span class="text-xs text-zinc-500 mr-1 mt-1">{{ msg.time }}</span>
          </div>

          <!-- AI Message -->
          <div v-else class="self-start max-w-[90%] flex flex-col items-start">
            <div class="bg-white/5 border border-white/10 text-primary px-3 py-2 rounded-2xl rounded-tl-none relative group font-medium tracking-wide break-all whitespace-pre-wrap">
               <div v-if="msg.isThinking" class="flex gap-1 h-5 items-center px-1">
                 <div class="w-1.5 h-1.5 bg-primary/50 rounded-full animate-bounce"></div>
                 <div class="w-1.5 h-1.5 bg-primary/50 rounded-full animate-bounce delay-100"></div>
                 <div class="w-1.5 h-1.5 bg-primary/50 rounded-full animate-bounce delay-200"></div>
               </div>
               <span v-else>{{ msg.content }}</span>
            </div>
            <span class="text-xs text-zinc-500 ml-1 mt-1">{{ msg.time }}</span>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="relative group">
        <input 
          ref="inputRef"
          v-model="inputDetails"
          @keydown.enter="sendMessage"
          type="text" 
          placeholder="输入指令控制机械臂..." 
          class="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-base text-white placeholder-zinc-500 focus:outline-none focus:border-primary/50 focus:bg-black/40 transition-all pr-10 font-medium"
          :disabled="isProcessing"
        >
        <button 
          @click="sendMessage"
          class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg hover:bg-white/10 text-zinc-500 hover:text-primary transition-colors disabled:opacity-50 cursor-pointer z-10 active:scale-90"
          :class="{ 'text-primary animate-pulse': inputDetails && !isProcessing }"
          :disabled="!inputDetails || isProcessing"
        >
          <span class="material-symbols-outlined text-xl">send</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'

const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  },
  isProcessing: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['send'])

const isCollapsed = ref(false)
const inputDetails = ref('')
const chatContainer = ref(null)
const inputRef = ref(null)

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}

function sendMessage() {
  if (!inputDetails.value.trim() || props.isProcessing) return
  emit('send', inputDetails.value)
  inputDetails.value = ''
  
  // 保持焦点
  nextTick(() => {
    inputRef.value?.focus()
  })
}

// Auto scroll to bottom
watch(() => props.messages.length, () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
})
</script>

<style scoped>
/* Scoped styles if needed, but using global utility classes mostly */
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
  background-color: transparent;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background-color: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  border: 1px solid transparent;
  background-clip: content-box;
  transition: all 0.3s ease;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: rgba(255, 255, 255, 0.2);
  border: 0px solid transparent;
}

/* Firefox support */
.custom-scrollbar {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.1) transparent;
}
</style>