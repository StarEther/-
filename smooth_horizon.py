#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
层位数据平滑处理工具
用于对层位标定数据进行平滑处理，减少噪声和异常值的影响

使用方法:
    python smooth_horizon.py input.dat output.dat [--method gaussian] [--sigma 1.0] [--window 3]

参数说明:
    input.dat    : 输入的层位数据文件
    output.dat   : 输出的平滑后数据文件
    --method     : 平滑方法 (gaussian/savgol/moving_average)，默认: gaussian
    --sigma      : 高斯平滑的标准差（仅用于gaussian方法），默认: 1.0
    --window     : 平滑窗口大小（用于savgol和moving_average），默认: 3

示例:
    python smooth_horizon.py input.dat output_smooth.dat
    python smooth_horizon.py input.dat output_smooth.dat --method savgol --window 5
    python smooth_horizon.py input.dat output_smooth.dat --method gaussian --sigma 2.0
"""

import numpy as np
from scipy import ndimage
from scipy.signal import savgol_filter
import argparse
import sys
import time


def read_horizon_file(filename):
    """
    读取层位文件
    
    参数:
        filename: 输入文件路径
        
    返回:
        header_lines: 文件头部信息（列表）
        data_points: 数据点列表，每个元素为字典 {'x', 'y', 'z', 'col', 'row'}
    """
    header_lines = []
    data_points = []
    in_header = True
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line_stripped = line.strip()
                
                if in_header or not line_stripped or line_stripped.startswith('#'):
                    header_lines.append(line)
                    if line_stripped.startswith('# End:'):
                        in_header = False
                    continue
                
                parts = line_stripped.split()
                if len(parts) >= 5:
                    try:
                        x = float(parts[0])
                        y = float(parts[1])
                        z = float(parts[2])
                        col = int(parts[3])
                        row = int(parts[4])
                        
                        data_points.append({
                            'x': x, 'y': y, 'z': z, 'col': col, 'row': row
                        })
                    except ValueError:
                        pass
    except FileNotFoundError:
        print(f"错误: 找不到文件 {filename}")
        sys.exit(1)
    except Exception as e:
        print(f"错误: 读取文件时出现问题: {e}")
        sys.exit(1)
    
    return header_lines, data_points


def smooth_gaussian(data_points, sigma=1.0):
    """
    使用高斯滤波进行平滑
    
    参数:
        data_points: 数据点列表
        sigma: 高斯平滑的标准差
        
    返回:
        平滑后的z值数组
    """
    # 构建网格
    cols = sorted(set(p['col'] for p in data_points))
    rows = sorted(set(p['row'] for p in data_points))
    
    col_to_idx = {col: i for i, col in enumerate(cols)}
    row_to_idx = {row: i for i, row in enumerate(rows)}
    
    # 创建z值网格
    z_grid = np.full((len(rows), len(cols)), np.nan)
    col_row_map = {}
    
    for p in data_points:
        col_idx = col_to_idx[p['col']]
        row_idx = row_to_idx[p['row']]
        z_grid[row_idx, col_idx] = p['z']
        col_row_map[(p['col'], p['row'])] = (p['x'], p['y'])
    
    # 使用高斯滤波平滑（只对非NaN值进行平滑）
    z_smoothed = ndimage.gaussian_filter(z_grid, sigma=sigma, mode='nearest')
    
    # 将结果映射回数据点
    smoothed_z_values = {}
    for p in data_points:
        col_idx = col_to_idx[p['col']]
        row_idx = row_to_idx[p['row']]
        smoothed_z_values[(p['col'], p['row'])] = z_smoothed[row_idx, col_idx]
    
    return smoothed_z_values


def smooth_savgol(data_points, window_length=3, polyorder=2):
    """
    使用Savitzky-Golay滤波器进行平滑
    
    参数:
        data_points: 数据点列表
        window_length: 窗口长度（必须为奇数）
        polyorder: 多项式阶数
        
    返回:
        平滑后的z值字典
    """
    # 确保窗口长度为奇数
    if window_length % 2 == 0:
        window_length += 1
    
    # 按列和行分组处理
    smoothed_z_values = {}
    
    # 按列处理
    cols = sorted(set(p['col'] for p in data_points))
    for col in cols:
        col_points = [p for p in data_points if p['col'] == col]
        col_points.sort(key=lambda p: p['row'])
        
        if len(col_points) >= window_length:
            z_values = np.array([p['z'] for p in col_points])
            z_smooth = savgol_filter(z_values, window_length, polyorder)
            for i, p in enumerate(col_points):
                smoothed_z_values[(p['col'], p['row'])] = z_smooth[i]
        else:
            # 如果点数太少，保持原值
            for p in col_points:
                smoothed_z_values[(p['col'], p['row'])] = p['z']
    
    # 按行处理（对列方向进行二次平滑）
    rows = sorted(set(p['row'] for p in data_points))
    for row in rows:
        row_points = [p for p in data_points if p['row'] == row]
        row_points.sort(key=lambda p: p['col'])
        
        if len(row_points) >= window_length:
            z_values = np.array([smoothed_z_values.get((p['col'], p['row']), p['z']) for p in row_points])
            z_smooth = savgol_filter(z_values, window_length, polyorder)
            for i, p in enumerate(row_points):
                # 取列方向和行方向的平均值
                original = smoothed_z_values.get((p['col'], p['row']), p['z'])
                smoothed_z_values[(p['col'], p['row'])] = (original + z_smooth[i]) / 2.0
        else:
            for p in row_points:
                if (p['col'], p['row']) not in smoothed_z_values:
                    smoothed_z_values[(p['col'], p['row'])] = p['z']
    
    return smoothed_z_values


def smooth_moving_average(data_points, window=3):
    """
    使用移动平均进行平滑
    
    参数:
        data_points: 数据点列表
        window: 窗口大小
        
    返回:
        平滑后的z值字典
    """
    smoothed_z_values = {}
    
    # 按列处理
    cols = sorted(set(p['col'] for p in data_points))
    for col in cols:
        col_points = [p for p in data_points if p['col'] == col]
        col_points.sort(key=lambda p: p['row'])
        
        z_values = np.array([p['z'] for p in col_points])
        z_smooth = np.convolve(z_values, np.ones(window)/window, mode='same')
        
        for i, p in enumerate(col_points):
            smoothed_z_values[(p['col'], p['row'])] = z_smooth[i]
    
    # 按行处理
    rows = sorted(set(p['row'] for p in data_points))
    for row in rows:
        row_points = [p for p in data_points if p['row'] == row]
        row_points.sort(key=lambda p: p['col'])
        
        z_values = np.array([smoothed_z_values.get((p['col'], p['row']), p['z']) for p in row_points])
        z_smooth = np.convolve(z_values, np.ones(window)/window, mode='same')
        
        for i, p in enumerate(row_points):
            original = smoothed_z_values.get((p['col'], p['row']), p['z'])
            smoothed_z_values[(p['col'], p['row'])] = (original + z_smooth[i]) / 2.0
    
    return smoothed_z_values


def smooth_horizon(input_file, output_file, method='gaussian', sigma=1.0, window=3):
    """
    平滑层位数据主函数
    
    参数:
        input_file: 输入文件路径
        output_file: 输出文件路径
        method: 平滑方法 ('gaussian', 'savgol', 'moving_average')
        sigma: 高斯平滑的标准差
        window: 平滑窗口大小
    """
    print("=" * 70)
    print("层位数据平滑处理工具")
    print("=" * 70)
    print()
    
    print(f"读取文件: {input_file}")
    start_time = time.time()
    
    header_lines, data_points = read_horizon_file(input_file)
    print(f"读取到 {len(data_points)} 个数据点")
    
    if len(data_points) == 0:
        print("错误: 没有读取到数据点")
        return
    
    read_time = time.time() - start_time
    print(f"读取耗时: {read_time:.2f} 秒\n")
    
    # 执行平滑
    print(f"使用 {method} 方法进行平滑处理...")
    smooth_start = time.time()
    
    if method == 'gaussian':
        smoothed_z = smooth_gaussian(data_points, sigma=sigma)
        print(f"高斯平滑参数: sigma = {sigma}")
    elif method == 'savgol':
        smoothed_z = smooth_savgol(data_points, window_length=window)
        print(f"Savitzky-Golay平滑参数: window = {window}")
    elif method == 'moving_average':
        smoothed_z = smooth_moving_average(data_points, window=window)
        print(f"移动平均平滑参数: window = {window}")
    else:
        print(f"错误: 未知的平滑方法 '{method}'")
        print("支持的方法: gaussian, savgol, moving_average")
        return
    
    smooth_time = time.time() - smooth_start
    print(f"平滑处理耗时: {smooth_time:.2f} 秒\n")
    
    # 写入文件
    print("写入文件...")
    write_start = time.time()
    
    # 按col和row排序
    sorted_points = sorted(data_points, key=lambda p: (p['col'], p['row']))
    
    with open(output_file, 'w', encoding='utf-8') as f_out:
        # 写入头部
        for line in header_lines:
            f_out.write(line)
        
        # 写入平滑后的数据点
        for p in sorted_points:
            col, row = p['col'], p['row']
            x, y = p['x'], p['y']
            z = smoothed_z.get((col, row), p['z'])  # 如果找不到，使用原值
            
            f_out.write(f"{x:>15.5f}   {y:>15.5f}   {z:>12.5f}     {col:>6}         {row:>10}\n")
    
    write_time = time.time() - write_start
    total_time = time.time() - start_time
    
    print(f"写入耗时: {write_time:.2f} 秒")
    print(f"\n完成!")
    print(f"总点数: {len(sorted_points)}")
    print(f"总耗时: {total_time:.2f} 秒")
    print(f"文件已保存: {output_file}")
    print("=" * 70)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='层位数据平滑处理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python smooth_horizon.py input.dat output_smooth.dat
  python smooth_horizon.py input.dat output_smooth.dat --method savgol --window 5
  python smooth_horizon.py input.dat output_smooth.dat --method gaussian --sigma 2.0
  python smooth_horizon.py input.dat output_smooth.dat --method moving_average --window 7
        """
    )
    
    parser.add_argument('input_file', help='输入的层位数据文件路径')
    parser.add_argument('output_file', help='输出的平滑后数据文件路径')
    parser.add_argument('--method', choices=['gaussian', 'savgol', 'moving_average'],
                       default='gaussian', help='平滑方法 (默认: gaussian)')
    parser.add_argument('--sigma', type=float, default=1.0,
                       help='高斯平滑的标准差 (默认: 1.0)')
    parser.add_argument('--window', type=int, default=3,
                       help='平滑窗口大小，用于savgol和moving_average方法 (默认: 3)')
    
    args = parser.parse_args()
    
    smooth_horizon(
        args.input_file,
        args.output_file,
        method=args.method,
        sigma=args.sigma,
        window=args.window
    )


if __name__ == '__main__':
    main()

