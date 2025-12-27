# -
**纯ai生成，可以读取并平滑你的手动层位标定，适用于smi地震波形指示反演软件导出数据。以及插值，用于加密你的层位标定。（加密点，如果需要实线表示还是需要手动连线一次）
大量数据不建议用自己电脑算，建议用云算力平台计算。
完成时间可以参考:32 vCPU Intel(R) Xeon(R) Platinum 8352V CPU @ 2.10GHz实测速度：平滑需要15分钟，增加插值20万左右的点（4×4改2×2）在23分钟跑完。**

# 层位数据处理工具

这是一套用于处理地震层位标定数据的开源工具，包含平滑和插值两个主要功能。

## 功能说明

### 1. 平滑功能 (`smooth_horizon.py`)

对层位标定数据进行平滑处理，减少噪声和异常值的影响，使数据更加连续和稳定。

**支持的平滑方法：**
- **高斯平滑 (gaussian)**: 使用高斯滤波进行平滑，适合大多数情况
- **Savitzky-Golay平滑 (savgol)**: 保持数据特征的平滑方法，适合需要保留局部特征的场景
- **移动平均 (moving_average)**: 简单快速的平滑方法

### 2. 插值功能 (`interpolate_horizon.py`)

在现有层位数据点之间插入新点，提高数据密度，使层位数据更加完整。

**支持的插值方法：**
- **线性插值 (linear)**: 默认方法，速度快，适合大多数情况
- **三次插值 (cubic)**: 更平滑的插值结果，但计算较慢
- **最近邻插值 (nearest)**: 最快的插值方法，但结果较粗糙

## 安装要求

```bash
pip install numpy scipy
```

## 使用方法

### 平滑功能

**基本用法：**
```bash
python smooth_horizon.py input.dat output_smooth.dat
```

**使用高斯平滑（指定标准差）：**
```bash
python smooth_horizon.py input.dat output_smooth.dat --method gaussian --sigma 2.0
```

**使用Savitzky-Golay平滑：**
```bash
python smooth_horizon.py input.dat output_smooth.dat --method savgol --window 5
```

**使用移动平均：**
```bash
python smooth_horizon.py input.dat output_smooth.dat --method moving_average --window 7
```

**参数说明：**
- `input_file`: 输入的层位数据文件（.dat格式）
- `output_file`: 输出的平滑后数据文件
- `--method`: 平滑方法，可选值：`gaussian`（默认）、`savgol`、`moving_average`
- `--sigma`: 高斯平滑的标准差（仅用于gaussian方法），默认: 1.0
- `--window`: 平滑窗口大小（用于savgol和moving_average方法），默认: 3

### 插值功能

**基本用法：**
```bash
python interpolate_horizon.py input.dat output_interp.dat
```

**指定插值间隔：**
```bash
python interpolate_horizon.py input.dat output_interp.dat --spacing 2
```

**使用三次插值：**
```bash
python interpolate_horizon.py input.dat output_interp.dat --spacing 1 --method cubic
```

**使用最近邻插值：**
```bash
python interpolate_horizon.py input.dat output_interp.dat --spacing 3 --method nearest
```

**参数说明：**
- `input_file`: 输入的层位数据文件（.dat格式）
- `output_file`: 输出的插值后数据文件
- `--spacing`: 目标间隔（在原始点之间插入新点的间隔），默认: 2
- `--method`: 插值方法，可选值：`linear`（默认）、`cubic`、`nearest`

## 数据格式

输入和输出文件使用标准的层位数据格式（.dat文件），包含：

1. **文件头部**：以 `#` 开头的注释行，包含元数据信息
2. **数据行**：每行包含5个字段，格式为：
   ```
   x坐标    y坐标    z坐标    col列号    row行号
   ```

示例：
```
# XYZCR Format Horizon File From SMI
# Type: scattered data
# ...
# End:
569628.57069   4968452.90755   1676.06000     35           586
569637.23152   4968447.90755   1676.10700     35           587
...
```

## 使用示例

### 示例1：先平滑再插值

```bash
# 第一步：对原始数据进行平滑
python smooth_horizon.py raw_data.dat smoothed_data.dat --method gaussian --sigma 1.5

# 第二步：对平滑后的数据进行插值
python interpolate_horizon.py smoothed_data.dat final_data.dat --spacing 2 --method linear
```

### 示例2：直接插值

```bash
# 直接对原始数据进行插值，提高数据密度
python interpolate_horizon.py raw_data.dat dense_data.dat --spacing 1 --method cubic
```

### 示例3：使用不同的平滑方法

```bash
# 使用Savitzky-Golay平滑，保留更多细节
python smooth_horizon.py input.dat output.dat --method savgol --window 5

# 使用移动平均，快速平滑
python smooth_horizon.py input.dat output.dat --method moving_average --window 7
```

## 注意事项

1. **文件编码**：工具使用UTF-8编码读取和写入文件，确保您的数据文件也是UTF-8编码
2. **数据格式**：确保输入文件符合标准格式，包含正确的头部信息和数据行
3. **内存使用**：对于非常大的数据集，插值功能可能需要较多内存
4. **参数选择**：
   - 平滑参数：较小的sigma或window值会产生更轻微的平滑效果
   - 插值间隔：较小的spacing值会产生更多的插值点，但处理时间更长

## 输出信息

工具运行时会显示详细的处理信息，包括：
- 读取的数据点数量
- 处理进度和耗时
- 生成的新点数量（插值功能）
- 文件保存位置

## 许可证

本工具开源免费使用，欢迎分享和改进。

## 贡献

cursor ai

