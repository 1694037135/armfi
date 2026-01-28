package com.robot;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 机械臂控制系统主启动类
 */
@SpringBootApplication
public class RobotControlApplication {
    public static void main(String[] args) {
        SpringApplication.run(RobotControlApplication.class, args);
        System.out.println("=================================");
        System.out.println("机械臂控制系统后端启动成功！");
        System.out.println("WebSocket地址: ws://localhost:8080/ws");
        System.out.println("=================================");
    }
}
