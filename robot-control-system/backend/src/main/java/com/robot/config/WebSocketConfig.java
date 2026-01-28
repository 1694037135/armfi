package com.robot.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.*;

/**
 * WebSocket配置类
 * 用于实现前后端实时通信
 */
@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    /**
     * 配置消息代理
     * /topic - 用于广播消息（如机械臂状态更新）
     * /app - 用于接收客户端消息
     */
    @Override
    public void configureMessageBroker(MessageBrokerRegistry config) {
        // 启用简单消息代理，用于向客户端推送消息
        config.enableSimpleBroker("/topic", "/queue");
        // 设置客户端发送消息的前缀
        config.setApplicationDestinationPrefixes("/app");
    }

    /**
     * 注册WebSocket端点
     * 前端通过这个端点建立WebSocket连接
     */
    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        registry.addEndpoint("/ws")
                .setAllowedOriginPatterns("*")  // 允许跨域
                .withSockJS();  // 启用SockJS支持（兼容不支持WebSocket的浏览器）
    }
}
