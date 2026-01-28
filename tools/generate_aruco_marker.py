#!/usr/bin/env python3
"""
ArUco 标记生成器 - 本地生成标定用的 ArUco 标记
无需访问外部网站
"""

import argparse
import sys
from pathlib import Path

try:
    import cv2
    import numpy as np
except ImportError as e:
    print(f"缺少依赖库: {e}")
    print("请运行: pip install opencv-contrib-python numpy")
    sys.exit(1)

# ArUco 字典类型
ARUCO_DICTS = {
    "4x4_50": cv2.aruco.DICT_4X4_50,
    "4x4_100": cv2.aruco.DICT_4X4_100,
    "4x4_250": cv2.aruco.DICT_4X4_250,
    "4x4_1000": cv2.aruco.DICT_4X4_1000,
    "5x5_50": cv2.aruco.DICT_5X5_50,
    "5x5_100": cv2.aruco.DICT_5X5_100,
    "5x5_250": cv2.aruco.DICT_5X5_250,
    "5x5_1000": cv2.aruco.DICT_5X5_1000,
    "6x6_50": cv2.aruco.DICT_6X6_50,
    "6x6_100": cv2.aruco.DICT_6X6_100,
    "6x6_250": cv2.aruco.DICT_6X6_250,
    "6x6_1000": cv2.aruco.DICT_6X6_1000,
}


def generate_marker(marker_id, dict_type="4x4_50", size=200, border=1):
    """
    生成单个 ArUco 标记
    
    Args:
        marker_id: 标记 ID
        dict_type: 字典类型
        size: 标记尺寸 (像素)
        border: 边框宽度 (单位: 标记方块)
    
    Returns:
        numpy array: 生成的标记图像
    """
    if dict_type not in ARUCO_DICTS:
        raise ValueError(f"不支持的字典类型: {dict_type}. 可用: {list(ARUCO_DICTS.keys())}")
    
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICTS[dict_type])
    marker_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, size, borderBits=border)
    
    return marker_img


def create_printable_sheet(marker_ids, dict_type="4x4_50", marker_size=200, 
                          sheet_size=(2480, 3508), margin=100, spacing=50):
    """
    创建可打印的 A4 标记表 (适合打印)
    
    Args:
        marker_ids: 标记 ID 列表
        dict_type: 字典类型
        marker_size: 每个标记的尺寸
        sheet_size: 纸张尺寸 (A4 @ 300dpi = 2480x3508)
        margin: 页边距
        spacing: 标记间距
    
    Returns:
        numpy array: A4 尺寸的图像
    """
    # 创建白色背景
    sheet = np.ones((sheet_size[1], sheet_size[0]), dtype=np.uint8) * 255
    
    # 计算布局
    usable_width = sheet_size[0] - 2 * margin
    usable_height = sheet_size[1] - 2 * margin
    
    cols = (usable_width + spacing) // (marker_size + spacing)
    rows = (usable_height + spacing) // (marker_size + spacing)
    
    # 生成并放置标记
    for idx, marker_id in enumerate(marker_ids[:rows * cols]):
        row = idx // cols
        col = idx % cols
        
        # 计算位置
        x = margin + col * (marker_size + spacing)
        y = margin + row * (marker_size + spacing)
        
        # 生成标记
        marker = generate_marker(marker_id, dict_type, marker_size)
        
        # 放置标记
        sheet[y:y+marker_size, x:x+marker_size] = marker
        
        # 添加 ID 标签
        label = f"ID: {marker_id}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        
        (text_width, text_height), _ = cv2.getTextSize(label, font, font_scale, thickness)
        text_x = x + (marker_size - text_width) // 2
        text_y = y + marker_size + 20
        
        cv2.putText(sheet, label, (text_x, text_y), font, font_scale, 0, thickness)
    
    return sheet


def main():
    parser = argparse.ArgumentParser(
        description="ArUco 标记生成器 - 用于摄像头标定",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 生成单个标记 (ID=0)
  python generate_aruco_marker.py --id 0 --output marker_0.png
  
  # 生成高分辨率标记
  python generate_aruco_marker.py --id 5 --size 400 --output marker_5.png
  
  # 生成可打印的 A4 标记表 (包含 ID 0-11)
  python generate_aruco_marker.py --sheet --ids 0 1 2 3 4 5 6 7 8 9 10 11 --output markers_sheet.png
  
  # 使用不同字典
  python generate_aruco_marker.py --id 0 --dict 6x6_250 --output marker_6x6.png
        """
    )
    
    parser.add_argument('--id', type=int, help='单个标记 ID')
    parser.add_argument('--ids', type=int, nargs='+', help='多个标记 ID (用于生成标记表)')
    parser.add_argument('--dict', type=str, default='4x4_50', 
                       choices=list(ARUCO_DICTS.keys()),
                       help='ArUco 字典类型 (默认: 4x4_50)')
    parser.add_argument('--size', type=int, default=200, help='标记尺寸 (像素, 默认: 200)')
    parser.add_argument('--border', type=int, default=1, help='边框宽度 (默认: 1)')
    parser.add_argument('--sheet', action='store_true', help='生成 A4 打印表')
    parser.add_argument('--output', '-o', type=str, help='输出文件路径')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🏷️  ArUco 标记生成器")
    print("=" * 60)
    
    # 生成 A4 标记表
    if args.sheet:
        if not args.ids:
            print("错误: 使用 --sheet 时必须指定 --ids")
            sys.exit(1)
        
        print(f"生成标记表 (字典: {args.dict}, 标记数: {len(args.ids)})")
        sheet = create_printable_sheet(args.ids, args.dict, args.size)
        
        output_path = args.output or f"aruco_sheet_{args.dict}.png"
        cv2.imwrite(output_path, sheet)
        
        print(f"✓ 已生成 A4 标记表: {output_path}")
        print(f"  包含标记: {args.ids}")
        print(f"  建议使用 A4 纸打印 (300 DPI)")
        
    # 生成单个标记
    elif args.id is not None:
        print(f"生成标记 (ID: {args.id}, 字典: {args.dict}, 尺寸: {args.size}x{args.size})")
        marker = generate_marker(args.id, args.dict, args.size, args.border)
        
        output_path = args.output or f"aruco_marker_{args.id}.png"
        cv2.imwrite(output_path, marker)
        
        print(f"✓ 已生成标记: {output_path}")
        print(f"  ID: {args.id}")
        print(f"  尺寸: {args.size}x{args.size} 像素")
        
    else:
        print("错误: 必须指定 --id 或 --sheet")
        parser.print_help()
        sys.exit(1)
    
    print("\n使用提示:")
    print("  1. 将生成的图像打印到纸上")
    print("  2. 确保打印质量清晰,避免模糊")
    print("  3. 标记周围需要白色边框")
    print("  4. 在摄像头标定时放置在工作区域")
    print("=" * 60)


if __name__ == '__main__':
    main()
