package com.robot.controller;

import com.robot.model.ControlCommand;
import com.robot.service.SerialPortService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.SendTo;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.*;

/**
 * 机械臂控制器
 * 处理前端发来的控制命令
 */
@Slf4j
@Controller
@RequiredArgsConstructor
public class RobotController {

    private final SerialPortService serialPortService;

    /**
     * WebSocket消息处理：WASD控制
     * 前端发送到 /app/control，后端广播到 /topic/status
     */
    @MessageMapping("/control")
    @SendTo("/topic/status")
    public String handleControl(ControlCommand command) {
        log.info("收到控制命令: {}", command);

        switch (command.getType()) {
            case "keyboard":
                // WASD键盘控制
                handleKeyboardControl(command);
                break;
            case "stop":
                serialPortService.sendRemoteEvent(0, 0, 0);
                break;
            case "auto":
                // 自动移动到指定位置
                handleAutoMove(command);
                break;
            case "reset":
                // 复位
                serialPortService.softReset();
                break;
            case "move_to_angles":
                handleMoveToAngles(command);
                break;
            default:
                log.warn("未知命令类型: {}", command.getType());
        }

        return "命令已执行: " + command.getType();
    }

    /**
     * 处理多关节绝对角度移动
     * 将弧度转换为度数并发送
     */
    private void handleMoveToAngles(ControlCommand command) {
        if (command.getAngles() != null && command.getAngles().size() == 6) {
            for (int i = 0; i < 6; i++) {
                // 前端发来的是弧度，转换为度数
                double angleRad = command.getAngles().get(i);
                double angleDeg = Math.toDegrees(angleRad);
                
                // 发送绝对角度命令 (关节ID从1开始)
                serialPortService.sendAbsRotate(i + 1, angleDeg);
                
                // 稍微延时避免串口缓冲区溢出 (可选，视波特率而定)
                try { Thread.sleep(10); } catch (InterruptedException e) {}
            }
        }
    }

    /**
     * 处理键盘控制
     */
    private void handleKeyboardControl(ControlCommand command) {
        String key = command.getKey();
        double speed = command.getSpeed() != null ? command.getSpeed() : 1.0;

        double vx = 0, vy = 0, vz = 0;

        switch (key.toLowerCase()) {
            case "w": vy = speed; break;   // 前进
            case "s": vy = -speed; break;  // 后退
            case "a": vx = -speed; break;  // 左移
            case "d": vx = speed; break;   // 右移
            case "q": vz = speed; break;   // 上升
            case "e": vz = -speed; break;  // 下降
        }

        serialPortService.sendRemoteEvent(vx, vy, vz);
    }

    /**
     * 处理自动移动
     */
    private void handleAutoMove(ControlCommand command) {
        if (command.getX() != null && command.getY() != null && command.getZ() != null) {
            serialPortService.sendAutoMove(
                command.getX(),
                command.getY(),
                command.getZ()
            );
        }
    }

    /**
     * REST API：获取串口状态
     */
    @GetMapping("/api/status")
    @ResponseBody
    public String getStatus() {
        return serialPortService.isConnected() ? "connected" : "disconnected";
    }

    /**
     * REST API：测试连接
     */
    @PostMapping("/api/test")
    @ResponseBody
    public String testConnection() {
        serialPortService.sendCommand("soft_reset");
        return "测试命令已发送";
    }
}
