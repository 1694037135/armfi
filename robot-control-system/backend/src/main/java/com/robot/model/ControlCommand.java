package com.robot.model;

import lombok.Data;
import java.util.List;

/**
 * 控制命令模型
 */
@Data
public class ControlCommand {
    private String type;      // 命令类型: keyboard, auto, reset
    private String key;       // 按键: w, a, s, d, q, e
    private Double speed;     // 速度: 0.0 - 1.0
    private Double x;         // 目标X坐标
    private Double y;         // 目标Y坐标
    private Double z;         // 目标Z坐标
    private String mode;
    private Integer jointId;
    private Double angle;
    private List<Double> angles;
}
