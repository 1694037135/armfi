package com.robotarm.controller;

import org.springframework.web.bind.annotation.*;
import java.util.*;

/**
 * 简单逆运动学控制器
 * 使用几何方法计算关节角度，无需深度学习训练
 */
@RestController
@RequestMapping("/api/ik")
@CrossOrigin(origins = "*")
public class SimpleIKController {
    
    /**
     * 计算到达目标位置的关节角度
     * 使用简化的几何逆运动学
     */
    @PostMapping("/calculate")
    public Map<String, Object> calculateIK(@RequestBody Map<String, Object> request) {
        try {
            // 获取目标位置
            double targetX = ((Number) request.get("x")).doubleValue();
            double targetY = ((Number) request.get("y")).doubleValue();
            double targetZ = ((Number) request.get("z")).doubleValue();
            
            // 机械臂参数（单位：米）
            double L1 = 0.166;  // 底座到关节1的高度
            double L2 = 0.200;  // 关节2到关节3的长度
            double L3 = 0.185;  // 关节3到关节4的长度
            double L4 = 0.125;  // 关节4到末端的长度
            
            // 计算关节角度
            Map<String, Double> angles = calculateAngles(targetX, targetY, targetZ, L1, L2, L3, L4);
            
            // 检查是否可达
            boolean reachable = angles != null;
            
            Map<String, Object> response = new HashMap<>();
            response.put("success", reachable);
            response.put("target", Map.of("x", targetX, "y", targetY, "z", targetZ));
            
            if (reachable) {
                response.put("angles", angles);
                response.put("message", "目标位置可达");
            } else {
                response.put("message", "目标位置超出机械臂工作范围");
            }
            
            return response;
            
        } catch (Exception e) {
            Map<String, Object> error = new HashMap<>();
            error.put("success", false);
            error.put("error", e.getMessage());
            return error;
        }
    }
    
    /**
     * 预定义位置快速访问
     */
    @GetMapping("/preset/{position}")
    public Map<String, Object> getPresetPosition(@PathVariable String position) {
        Map<String, double[]> presets = new HashMap<>();
        
        // 定义常用位置（x, y, z）
        presets.put("home", new double[]{0.0, -0.25, 0.3});      // 初始位置
        presets.put("left", new double[]{-0.15, -0.25, 0.25});   // 左侧
        presets.put("right", new double[]{0.15, -0.25, 0.25});   // 右侧
        presets.put("center", new double[]{0.0, -0.30, 0.20});   // 中心低位
        presets.put("high", new double[]{0.0, -0.20, 0.40});     // 高位
        presets.put("pickup", new double[]{0.10, -0.30, 0.15});  // 拾取位置
        
        double[] target = presets.getOrDefault(position, presets.get("home"));
        
        Map<String, Object> request = new HashMap<>();
        request.put("x", target[0]);
        request.put("y", target[1]);
        request.put("z", target[2]);
        
        return calculateIK(request);
    }
    
    /**
     * 简化的逆运动学计算
     * 使用几何方法求解6自由度机械臂
     */
    private Map<String, Double> calculateAngles(double x, double y, double z, 
                                                 double L1, double L2, double L3, double L4) {
        try {
            Map<String, Double> angles = new HashMap<>();
            
            // 关节1：底座旋转（绕Z轴）
            double theta1 = Math.atan2(x, -y);  // 注意坐标系
            angles.put("joint1", Math.toDegrees(theta1));
            
            // 计算在XY平面的投影距离
            double r = Math.sqrt(x * x + y * y);
            
            // 调整目标高度（减去末端执行器长度）
            double targetHeight = z - L1;
            double targetReach = r - L4 * 0.5;  // 简化：假设末端水平
            
            // 检查是否在工作范围内
            double maxReach = L2 + L3;
            double minReach = Math.abs(L2 - L3);
            double actualReach = Math.sqrt(targetReach * targetReach + targetHeight * targetHeight);
            
            if (actualReach > maxReach || actualReach < minReach) {
                return null;  // 不可达
            }
            
            // 关节2和关节3：使用余弦定理
            double cosAngle3 = (actualReach * actualReach - L2 * L2 - L3 * L3) / (2 * L2 * L3);
            cosAngle3 = Math.max(-1.0, Math.min(1.0, cosAngle3));  // 限制在[-1, 1]
            
            double theta3 = Math.acos(cosAngle3);
            angles.put("joint3", Math.toDegrees(theta3));
            
            // 关节2
            double alpha = Math.atan2(targetHeight, targetReach);
            double beta = Math.atan2(L3 * Math.sin(theta3), L2 + L3 * Math.cos(theta3));
            double theta2 = alpha - beta;
            angles.put("joint2", Math.toDegrees(theta2));
            
            // 关节4、5、6：简化为保持末端水平
            double theta4 = 0.0;  // 简化
            double theta5 = -(theta2 + theta3);  // 保持末端水平
            double theta6 = 0.0;  // 简化
            
            angles.put("joint4", Math.toDegrees(theta4));
            angles.put("joint5", Math.toDegrees(theta5));
            angles.put("joint6", Math.toDegrees(theta6));
            
            return angles;
            
        } catch (Exception e) {
            return null;
        }
    }
    
    /**
     * 语音指令解析
     * 将自然语言转换为目标位置
     */
    @PostMapping("/voice-command")
    public Map<String, Object> parseVoiceCommand(@RequestBody Map<String, String> request) {
        String command = request.get("command").toLowerCase();
        
        Map<String, Object> response = new HashMap<>();
        
        // 解析指令
        if (command.contains("左") || command.contains("left")) {
            return getPresetPosition("left");
        } else if (command.contains("右") || command.contains("right")) {
            return getPresetPosition("right");
        } else if (command.contains("中") || command.contains("center")) {
            return getPresetPosition("center");
        } else if (command.contains("高") || command.contains("up") || command.contains("high")) {
            return getPresetPosition("high");
        } else if (command.contains("低") || command.contains("down") || command.contains("low")) {
            return getPresetPosition("pickup");
        } else if (command.contains("初始") || command.contains("home") || command.contains("复位")) {
            return getPresetPosition("home");
        } else if (command.contains("拿") || command.contains("捡") || command.contains("抓")) {
            return getPresetPosition("pickup");
        } else {
            response.put("success", false);
            response.put("message", "无法识别的指令: " + command);
            return response;
        }
    }
}
