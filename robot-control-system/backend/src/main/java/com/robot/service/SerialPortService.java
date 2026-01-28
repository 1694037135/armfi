package com.robot.service;

import com.fazecast.jSerialComm.SerialPort;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * 串口通信服务
 * 负责与STM32机械臂主控通信
 */
@Slf4j
@Service
public class SerialPortService {

    @Value("${serial.port:COM3}")
    private String portName;

    @Value("${serial.baudrate:115200}")
    private int baudRate;

    @Value("${serial.enabled:false}")
    private boolean enabled;

    private SerialPort comPort;
    private boolean isConnected = false;

    /**
     * 初始化串口连接
     */
    @PostConstruct
    public void init() {
        if (!enabled) {
            log.warn("串口功能未启用，使用模拟模式");
            return;
        }

        try {
            // 列出所有可用串口
            SerialPort[] ports = SerialPort.getCommPorts();
            log.info("可用串口列表:");
            for (SerialPort port : ports) {
                log.info("  - {}", port.getSystemPortName());
            }

            // 打开指定串口
            comPort = SerialPort.getCommPort(portName);
            comPort.setBaudRate(baudRate);
            comPort.setNumDataBits(8);
            comPort.setNumStopBits(1);
            comPort.setParity(SerialPort.NO_PARITY);

            if (comPort.openPort()) {
                isConnected = true;
                log.info("串口 {} 打开成功，波特率: {}", portName, baudRate);
                
                // 发送初始化命令
                sendCommand("remote_enable");
            } else {
                log.error("串口 {} 打开失败", portName);
            }
        } catch (Exception e) {
            log.error("串口初始化失败: {}", e.getMessage());
        }
    }

    /**
     * 发送命令到机械臂
     * @param command 命令字符串，如 "remote_event 0.0 1.0 0.0 0.0 0.0 0.0"
     */
    public void sendCommand(String command) {
        if (!enabled) {
            log.debug("[模拟模式] 发送命令: {}", command);
            return;
        }

        if (!isConnected || comPort == null) {
            log.warn("串口未连接，无法发送命令: {}", command);
            return;
        }

        try {
            String fullCommand = command + "\n";
            byte[] bytes = fullCommand.getBytes();
            int written = comPort.writeBytes(bytes, bytes.length);
            
            if (written > 0) {
                log.debug("发送命令成功: {}", command);
            } else {
                log.warn("发送命令失败: {}", command);
            }
        } catch (Exception e) {
            log.error("发送命令异常: {}", e.getMessage());
        }
    }

    /**
     * 发送WASD控制命令
     * @param vx X轴速度 (-1.0 到 1.0)
     * @param vy Y轴速度 (-1.0 到 1.0)
     * @param vz Z轴速度 (-1.0 到 1.0)
     */
    public void sendRemoteEvent(double vx, double vy, double vz) {
        double p0 = -vx;
        double p1 = vy;
        double p2 = 0.0;
        double p3 = 0.0;
        double p4 = vz;
        double p5 = -vz;
        String command = String.format("remote_event %.2f %.2f %.2f %.2f %.2f %.2f", p0, p1, p2, p3, p4, p5);
        sendCommand(command);
    }

    /**
     * 发送自动移动命令
     * @param x 目标X坐标
     * @param y 目标Y坐标
     * @param z 目标Z坐标
     */
    public void sendAutoMove(double x, double y, double z) {
        String command = String.format("auto %.3f %.3f %.3f", x, y, z);
        sendCommand(command);
    }

    /**
     * 发送绝对角度控制命令
     * @param jointId 关节ID (1-6)
     * @param angle 角度 (度)
     */
    public void sendAbsRotate(int jointId, double angle) {
        String command = String.format("abs_rotate %d %.2f 0 0 0 0", jointId, angle);
        sendCommand(command);
    }

    /**
     * 发送相对角度控制命令
     * @param jointId 关节ID (1-6)
     * @param angle 角度 (度)
     */
    public void sendRelRotate(int jointId, double angle) {
        String command = String.format("rel_rotate %d %.2f 0 0 0 0", jointId, angle);
        sendCommand(command);
    }

    /**
     * 软复位（回到零点）
     */
    public void softReset() {
        sendCommand("soft_reset");
    }

    /**
     * 关闭串口
     */
    @PreDestroy
    public void close() {
        if (comPort != null && comPort.isOpen()) {
            sendCommand("remote_disable");
            comPort.closePort();
            log.info("串口已关闭");
        }
    }

    public boolean isConnected() {
        return isConnected;
    }
}
