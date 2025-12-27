#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
层位数据插值处理工具
用于在层位标定数据点之间插入新点，提高数据密度

使用方法:
    python interpolate_horizon.py input.dat output.dat [--spacing 2] [--method linear]

参数说明:
    input.dat    : 输入的层位数据文件
    output.dat   : 输出的插值后数据文件
    --spacing    : 目标间隔（在原始点之间插入新点的间隔），默认: 2
    --method     : 插值方法 (linear/cubic/nearest)，默认: linear

示例:
    python interpolate_horizon.py input.dat output_interp.dat
    python interpolate_horizon.py input.dat output_interp.dat --spacing 2
    python interpolate_horizon.py input.dat output_interp.dat --spacing 1 --method cubic
"""

import numpy as np
from scipy.interpolate import griddata
from collections import Counter
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


def interpolate_horizon(input_file, output_file, target_spacing=2, method='linear'):
    """
    在原始点之间插入新点
    
    参数:
        input_file: 输入文件路径
        output_file: 输出文件路径
        target_spacing: 目标间隔
        method: 插值方法 ('linear', 'cubic', 'nearest')
    """
    print("=" * 70)
    print("层位数据插值处理工具")
    print("=" * 70)
    print()
    
    print(f"读取文件: {input_file}")
    start_time = time.time()
    
    header_lines, data_points = read_horizon_file(input_file)
    print(f"读取到 {len(data_points)} 个原始数据点")
    
    if len(data_points) == 0:
        print("错误: 没有读取到数据点")
        return
    
    read_time = time.time() - start_time
    print(f"读取耗时: {read_time:.2f} 秒\n")
    
    # 建立原始数据点的映射
    col_row_map = {(p['col'], p['row']): (p['x'], p['y'], p['z']) for p in data_points}
    points_xy = np.array([[p['x'], p['y']] for p in data_points])
    values_z = np.array([p['z'] for p in data_points])
    
    # 分析每个col实际存在的row值，以及每个row实际存在的col值
    col_to_rows = {}  # {col: [sorted row values]}
    row_to_cols = {}  # {row: [sorted col values]}
    
    for p in data_points:
        col = p['col']
        row = p['row']
        if col not in col_to_rows:
            col_to_rows[col] = []
        if row not in row_to_cols:
            row_to_cols[row] = []
        col_to_rows[col].append(row)
        row_to_cols[row].append(col)
    
    # 排序
    for col in col_to_rows:
        col_to_rows[col] = sorted(set(col_to_rows[col]))
    for row in row_to_cols:
        row_to_cols[row] = sorted(set(row_to_cols[row]))
    
    print(f"有数据的列数: {len(col_to_rows)}")
    print(f"有数据的行数: {len(row_to_cols)}")
    
    # 计算当前间隔（检查同一col的不同row之间的间隔）
    row_intervals_all = []
    for col, rows in list(col_to_rows.items())[:100]:  # 检查前100个col
        if len(rows) > 1:
            for i in range(len(rows) - 1):
                interval = rows[i+1] - rows[i]
                if interval > 0:
                    row_intervals_all.append(interval)
    
    col_intervals_all = []
    for row, cols in list(row_to_cols.items())[:100]:  # 检查前100个row
        if len(cols) > 1:
            for i in range(len(cols) - 1):
                interval = cols[i+1] - cols[i]
                if interval > 0:
                    col_intervals_all.append(interval)
    
    # 找到最常见的间隔（排除1）
    if col_intervals_all:
        interval_counts = Counter(col_intervals_all)
        filtered = {k: v for k, v in interval_counts.items() if k > 1}
        if filtered:
            col_spacing = max(filtered.items(), key=lambda x: x[1])[0]
        else:
            col_spacing = 4
    else:
        col_spacing = 4
    
    if row_intervals_all:
        interval_counts = Counter(row_intervals_all)
        filtered = {k: v for k, v in interval_counts.items() if k > 1}
        if filtered:
            row_spacing = max(filtered.items(), key=lambda x: x[1])[0]
        else:
            row_spacing = 4
    else:
        row_spacing = 4
    
    print(f"当前列间隔: {col_spacing}, 行间隔: {row_spacing}")
    print(f"目标间隔: {target_spacing}")
    print(f"插值方法: {method}\n")
    
    # 生成新点：只在实际存在数据的col/row之间插入
    print("生成新点...")
    new_points = {}  # {(col, row): (x, y, z)}
    
    # 首先添加所有原始点
    for (col, row), (x, y, z) in col_row_map.items():
        new_points[(col, row)] = (x, y, z)
    
    # 对于每个col，在其实际存在的row值之间插入新row
    need_interp_points = []
    need_interp_indices = []
    
    for col, rows in col_to_rows.items():
        for i in range(len(rows) - 1):
            current_row = rows[i]
            next_row = rows[i+1]
            # 在current_row和next_row之间插入间隔为target_spacing的点
            for new_row in range(current_row + target_spacing, next_row, target_spacing):
                if (col, new_row) not in new_points:
                    need_interp_indices.append((col, new_row))
                    # 计算y坐标：基于同一col的相邻row点
                    y1 = col_row_map[(col, current_row)][1]
                    y2 = col_row_map[(col, next_row)][1]
                    ratio = (new_row - current_row) / (next_row - current_row)
                    new_y = y1 + (y2 - y1) * ratio
                    # x坐标：使用同一col的x坐标（因为同一col的x应该相同或接近）
                    new_x = col_row_map[(col, current_row)][0]
                    need_interp_points.append((new_x, new_y))
    
    # 对于每个row，在其实际存在的col值之间插入新col
    for row, cols in row_to_cols.items():
        for i in range(len(cols) - 1):
            current_col = cols[i]
            next_col = cols[i+1]
            # 在current_col和next_col之间插入间隔为target_spacing的点
            for new_col in range(current_col + target_spacing, next_col, target_spacing):
                if (new_col, row) not in new_points:
                    need_interp_indices.append((new_col, row))
                    # 计算x坐标：基于同一row的相邻col点
                    x1 = col_row_map[(current_col, row)][0]
                    x2 = col_row_map[(next_col, row)][0]
                    ratio = (new_col - current_col) / (next_col - current_col)
                    new_x = x1 + (x2 - x1) * ratio
                    # y坐标：使用同一row的y坐标
                    new_y = col_row_map[(current_col, row)][1]
                    need_interp_points.append((new_x, new_y))
    
    print(f"原始数据点: {len(new_points)} 个")
    print(f"需要插值: {len(need_interp_points)} 个")
    
    # 批量插值z值
    if len(need_interp_points) > 0:
        print(f"开始批量插值z值（方法: {method}）...\n")
        interp_start = time.time()
        
        interp_points_xy = np.array(need_interp_points)
        z_interpolated = griddata(points_xy, values_z, interp_points_xy, method=method, fill_value=np.nan)
        
        # 处理NaN值：使用nearest方法填充
        nan_mask = np.isnan(z_interpolated)
        if np.any(nan_mask):
            print(f"发现 {np.sum(nan_mask)} 个NaN值，使用nearest方法填充...")
            z_nearest = griddata(points_xy, values_z, interp_points_xy[nan_mask], method='nearest')
            z_interpolated[nan_mask] = z_nearest
        
        # 添加到结果
        for i, (new_col, new_row) in enumerate(need_interp_indices):
            new_points[(new_col, new_row)] = (need_interp_points[i][0], need_interp_points[i][1], float(z_interpolated[i]))
        
        interp_time = time.time() - interp_start
        print(f"批量插值完成，耗时: {int(interp_time//60)}分{int(interp_time%60)}秒")
        if interp_time > 0:
            print(f"平均速度: {int(len(need_interp_points)/interp_time)} 点/秒\n")
    else:
        print("无需插值新点\n")
    
    # 写入文件
    print("写入文件...")
    write_start = time.time()
    
    # 按col和row排序
    sorted_points = sorted(new_points.items(), key=lambda x: (x[0][0], x[0][1]))
    total_points = len(sorted_points)
    
    with open(output_file, 'w', encoding='utf-8') as f_out:
        # 写入头部
        for line in header_lines:
            f_out.write(line)
        
        # 写入所有点
        processed = 0
        for (col, row), (x, y, z) in sorted_points:
            f_out.write(f"{x:>15.5f}   {y:>15.5f}   {z:>12.5f}     {col:>6}         {row:>10}\n")
            processed += 1
            
            if processed % 10000 == 0:
                elapsed = time.time() - write_start
                percent = processed / total_points * 100
                speed = processed / elapsed if elapsed > 0 else 0
                remaining = (total_points - processed) / speed if speed > 0 else 0
                print(f"\r进度: {percent:.1f}% ({processed}/{total_points}) 速度: {int(speed)}点/秒 剩余: {int(remaining//60)}分{int(remaining%60)}秒", end='', flush=True)
    
    total_time = time.time() - start_time
    write_time = time.time() - write_start
    
    print(f"\n\n完成!")
    print(f"总点数: {processed}")
    print(f"原始数据点: {len(col_row_map)}")
    print(f"新增插值点: {len(need_interp_points)}")
    print(f"写入耗时: {write_time:.2f} 秒")
    print(f"总耗时: {int(total_time//60)}分{int(total_time%60)}秒")
    print(f"文件已保存: {output_file}")
    print("=" * 70)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='层位数据插值处理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python interpolate_horizon.py input.dat output_interp.dat
  python interpolate_horizon.py input.dat output_interp.dat --spacing 2
  python interpolate_horizon.py input.dat output_interp.dat --spacing 1 --method cubic
  python interpolate_horizon.py input.dat output_interp.dat --spacing 3 --method nearest
        """
    )
    
    parser.add_argument('input_file', help='输入的层位数据文件路径')
    parser.add_argument('output_file', help='输出的插值后数据文件路径')
    parser.add_argument('--spacing', type=int, default=2,
                       help='目标间隔（在原始点之间插入新点的间隔，默认: 2）')
    parser.add_argument('--method', choices=['linear', 'cubic', 'nearest'],
                       default='linear', help='插值方法 (默认: linear)')
    
    args = parser.parse_args()
    
    interpolate_horizon(
        args.input_file,
        args.output_file,
        target_spacing=args.spacing,
        method=args.method
    )


if __name__ == '__main__':
    main()

