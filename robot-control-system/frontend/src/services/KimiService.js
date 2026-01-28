
/**
 * LLMService.js (原 KimiService)
 * 负责与后端 LLM 代理进行通信，将自然语言转换为 JSON 指令
 * 包含防抖机制和速率限制保护
 */

export class KimiService {
    constructor() {
        this.lastRequestTime = 0;
        this.minInterval = 5000; // 最少间隔 5 秒 (更保守)
        this.pendingRequest = null; // 防抖队列
        this.debounceTimer = null;
    }

    /**
     * 发送文本给 LLM，获取 JSON 指令
     * @param {string} userText 用户说的话
     * @returns {Promise<Object>} 解析后的 JSON 指令
     */
    async optimizeCommand(userText) {
        if (!userText || !userText.trim()) return null;

        // 频率限制检查
        const now = Date.now();
        const timeSinceLastRequest = now - this.lastRequestTime;
        if (timeSinceLastRequest < this.minInterval) {
            const waitTime = Math.ceil((this.minInterval - timeSinceLastRequest) / 1000);
            console.warn(`[LLM] 请求过于频繁，排队等待 ${waitTime} 秒...`);
            // 不抛错，而是等待
            await this.sleep(this.minInterval - timeSinceLastRequest);
        }

        const BACKEND_URL = 'http://localhost:5000/api/llm/chat';

        try {
            this.lastRequestTime = Date.now();

            const response = await fetch(BACKEND_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: userText
                })
            });

            if (!response.ok) {
                throw new Error(`Backend Error: ${response.statusText}`);
            }

            const data = await response.json();

            if (!data.success) {
                // 特殊处理 429 错误 (后端已经重试过了)
                if (data.error && data.error.includes('限流')) {
                    console.warn('[LLM] 服务端重试后仍限流，请等待更长时间');
                }
                throw new Error(data.error || 'Unknown Backend Error');
            }

            return data.command;

        } catch (error) {
            console.error('LLM Service Request Failed', error);
            throw error;
        }
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

export const kimiService = new KimiService();
