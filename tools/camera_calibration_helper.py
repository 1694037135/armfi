#!/usr/bin/env python3
"""
摄像头标定辅助工具
支持 ArUco 标记自动检测和手动标定流程
"""

import argparse
import sys
import json
import numpy as np
from pathlib import Path
from datetime import datetime

try:
    import cv2
except ImportError:
    print("缺少依赖库: opencv-contrib-python")
    print("请运行: pip install opencv-contrib-python numpy")
    sys.exit(1)


class CalibrationHelper:
    def __init__(self, camera_source=0, aruco_dict="4x4_50", output_dir="calibration_data"):
        self.camera_source = camera_source
        self.cap = None
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # ArUco 检测器
        aruco_dict_map = {
            "4x4_50": cv2.aruco.DICT_4X4_50,
            "4x4_100": cv2.aruco.DICT_4X4_100,
            "5x5_50": cv2.aruco.DICT_5X5_50,
            "6x6_250": cv2.aruco.DICT_6X6_250,
        }
        
        if aruco_dict not in aruco_dict_map:
            aruco_dict = "4x4_50"
        
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(aruco_dict_map[aruco_dict])
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        
        # 标定点数据
        self.calibration_points = []  # [(u, v, x, y, z), ...]
        
    def open_camera(self):
        """打开摄像头"""
        if isinstance(self.camera_source, str) and self.camera_source.startswith('http'):
            # IP Camera
            self.cap = cv2.VideoCapture(self.camera_source)
        else:
            # 本地摄像头
            self.cap = cv2.VideoCapture(int(self.camera_source) if str(self.camera_source).isdigit() else self.camera_source)
        
        if not self.cap.isOpened():
            print(f"错误: 无法打开摄像头 {self.camera_source}")
            return False
        
        # 设置分辨率
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        print(f"✓ 摄像头已打开: {self.camera_source}")
        return True
    
    def detect_aruco(self, frame):
        """检测 ArUco 标记"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, rejected = self.detector.detectMarkers(gray)
        
        # 绘制检测结果
        if ids is not None:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)
            
            # 显示中心点
            for i, corner in enumerate(corners):
                # 计算中心点
                center = corner[0].mean(axis=0).astype(int)
                marker_id = ids[i][0]
                
                # 绘制中心点
                cv2.circle(frame, tuple(center), 5, (0, 255, 0), -1)
                cv2.putText(frame, f"ID:{marker_id}", 
                           (center[0] + 10, center[1] - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
            return corners, ids
        
        return None, None
    
    def add_calibration_point(self, image_point, world_point):
        """添加标定点"""
        u, v = image_point
        x, y, z = world_point
        self.calibration_points.append({
            "image": {"u": float(u), "v": float(v)},
            "world": {"x": float(x), "y": float(y), "z": float(z)}
        })
        print(f"✓ 已添加标定点 #{len(self.calibration_points)}: 图像({u}, {v}) -> 世界({x}, {y}, {z})")
    
    def compute_calibration_matrix(self):
        """计算标定矩阵 (仿射变换)"""
        if len(self.calibration_points) < 4:
            print(f"错误: 需要至少 4 个标定点,当前只有 {len(self.calibration_points)} 个")
            return None
        
        # 提取数据
        image_points = np.array([[p["image"]["u"], p["image"]["v"]] for p in self.calibration_points], dtype=np.float32)
        world_points = np.array([[p["world"]["x"], p["world"]["y"]] for p in self.calibration_points], dtype=np.float32)
        
        # 计算仿射变换矩阵
        matrix, _ = cv2.estimateAffine2D(image_points, world_points)
        
        if matrix is None:
            print("错误: 无法计算变换矩阵,请检查标定点是否合理")
            return None
        
        print("\n✓ 标定矩阵计算完成:")
        print(matrix)
        
        # 计算误差
        errors = []
        for i, point in enumerate(self.calibration_points):
            u, v = point["image"]["u"], point["image"]["v"]
            x_true, y_true = point["world"]["x"], point["world"]["y"]
            
            # 变换到世界坐标
            transformed = matrix @ np.array([u, v, 1])
            x_pred, y_pred = transformed
            
            error = np.sqrt((x_pred - x_true)**2 + (y_pred - y_true)**2)
            errors.append(error)
            print(f"  点 {i+1} 误差: {error:.2f} mm")
        
        mean_error = np.mean(errors)
        print(f"\n平均误差: {mean_error:.2f} mm")
        
        return matrix
    
    def save_calibration(self, matrix):
        """保存标定结果"""
        output_file = self.output_dir / f"calibration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "calibration_points": self.calibration_points,
            "transformation_matrix": matrix.tolist(),
            "num_points": len(self.calibration_points)
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ 标定结果已保存: {output_file}")
        return output_file
    
    def run_interactive_mode(self):
        """交互式标定模式"""
        if not self.open_camera():
            return
        
        print("\n" + "=" * 60)
        print("摄像头标定辅助工具 - 交互模式")
        print("=" * 60)
        print("\n操作说明:")
        print("  • 空格键: 捕获当前帧并添加标定点")
        print("  • 'a' 键: 自动检测 ArUco 标记")
        print("  • 'c' 键: 计算标定矩阵")
        print("  • 's' 键: 保存标定结果")
        print("  • 'q' 键: 退出")
        print("=" * 60 + "\n")
        
        aruco_detection = False
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("错误: 无法读取摄像头画面")
                break
            
            display_frame = frame.copy()
            
            # ArUco 检测模式
            if aruco_detection:
                corners, ids = self.detect_aruco(display_frame)
                
                # 显示提示
                cv2.putText(display_frame, "ArUco Detection ON (Press 'a' to toggle)", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(display_frame, "ArUco Detection OFF (Press 'a' to toggle)", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # 显示标定点数量
            cv2.putText(display_frame, f"Calibration Points: {len(self.calibration_points)}", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            # 显示已标定的点
            for i, point in enumerate(self.calibration_points):
                u, v = int(point["image"]["u"]), int(point["image"]["v"])
                cv2.circle(display_frame, (u, v), 8, (0, 255, 255), 2)
                cv2.putText(display_frame, str(i + 1), (u + 10, v - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            
            cv2.imshow("Camera Calibration Helper", display_frame)
            
            # 按键处理
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                print("\n退出标定工具")
                break
            elif key == ord('a'):
                aruco_detection = not aruco_detection
                print(f"ArUco 检测: {'开启' if aruco_detection else '关闭'}")
            elif key == ord(' '):
                # 手动添加标定点
                print("\n请输入标定点信息:")
                try:
                    u = float(input("  图像 u 坐标: "))
                    v = float(input("  图像 v 坐标: "))
                    x = float(input("  世界 x 坐标 (mm): "))
                    y = float(input("  世界 y 坐标 (mm): "))
                    z = float(input("  世界 z 坐标 (mm): "))
                    self.add_calibration_point((u, v), (x, y, z))
                except ValueError:
                    print("输入格式错误,已取消")
            elif key == ord('c'):
                # 计算标定矩阵
                matrix = self.compute_calibration_matrix()
                if matrix is not None:
                    self.current_matrix = matrix
            elif key == ord('s'):
                # 保存标定结果
                if hasattr(self, 'current_matrix'):
                    self.save_calibration(self.current_matrix)
                else:
                    print("错误: 请先计算标定矩阵 (按 'c' 键)")
        
        self.cap.release()
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(
        description="摄像头标定辅助工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 使用默认摄像头
  python camera_calibration_helper.py
  
  # 使用 IP Camera
  python camera_calibration_helper.py --camera http://192.168.1.100:8080/video
  
  # 指定 ArUco 字典
  python camera_calibration_helper.py --dict 6x6_250
        """
    )
    
    parser.add_argument('--camera', '-c', default='0', help='摄像头源 (设备索引或 URL)')
    parser.add_argument('--dict', '-d', default='4x4_50',
                       choices=['4x4_50', '4x4_100', '5x5_50', '6x6_250'],
                       help='ArUco 字典类型')
    parser.add_argument('--output', '-o', default='calibration_data', help='输出目录')
    
    args = parser.parse_args()
    
    helper = CalibrationHelper(
        camera_source=args.camera,
        aruco_dict=args.dict,
        output_dir=args.output
    )
    
    helper.run_interactive_mode()


if __name__ == '__main__':
    main()
