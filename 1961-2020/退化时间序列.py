import os
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from glob import glob
from matplotlib.colors import LinearSegmentedColormap

# --------------------------
# 1. 配置参数
# --------------------------
# 输入文件夹：存放多期冻土栅格（1=冻土，0=非冻土，3=退化区）
input_folder = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\degradation_results"
# 输出图片路径（可选，如需保存）
output_fig_path = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\picture\冻土变化时间序列.png"

# 颜色映射：蓝色-非冻土(0)、白色-冻土(1)、红色-退化区(3)
color_segments = [
    (0, '#0000FF'),  # 0-非冻土，蓝色
    (1, '#FFFFFF'),  # 1-冻土，白色
    (3, '#FF0000')  # 3-退化区，红色
]

# 提取值和颜色
values = np.array([cs[0] for cs in color_segments])
colors = [cs[1] for cs in color_segments]

# 归一化值到 [0,1] 范围
norm_values = (values - values.min()) / (values.max() - values.min())

# 修正：直接使用 matplotlib.colors 解析颜色字符串为 RGB 元组
rgb_colors = [tuple(int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)) for c in colors]

# 构建用于 LinearSegmentedColormap 的颜色段列表
cdict = {'red': [], 'green': [], 'blue': []}
for nv, rgb in zip(norm_values, rgb_colors):
    cdict['red'].append((nv, rgb[0], rgb[0]))
    cdict['green'].append((nv, rgb[1], rgb[1]))
    cdict['blue'].append((nv, rgb[2], rgb[2]))

# 创建自定义颜色映射
cmap = LinearSegmentedColormap('custom_cmap', cdict)

# --------------------------
# 2. 读取栅格数据 & 提取时间信息
# --------------------------
raster_paths = sorted(glob(os.path.join(input_folder, "*.tif")))  # 按文件名排序
data_list = []
time_labels = []

for path in raster_paths:
    # 读取栅格
    with rasterio.open(path) as ds:
        data = ds.read(1)
        data_list.append(data)

        # 从文件名提取时间标签（需适配实际命名，这里假设是 degradation_YYYYMMDD_YYYYMMDD.tif 格式）
        fname = os.path.basename(path).replace("degradation_", "").replace(".tif", "")
        time_labels.append(fname)  # 如 "1961_1965_1966_1970" 等

# --------------------------
# 3. 绘制时间序列图
# --------------------------
rows = 4  # 行数，按需调整
cols = 3  # 列数，按需调整
fig, axes = plt.subplots(rows, cols, figsize=(15, 20))
axes = axes.flatten()  # 转为一维数组方便遍历

for i, (data, ax) in enumerate(zip(data_list, axes)):
    # 绘制栅格
    im = ax.imshow(data, cmap=cmap, vmin=values.min(), vmax=values.max())
    ax.set_title(time_labels[i], fontsize=10)
    ax.axis('off')  # 隐藏坐标轴

# 调整布局
plt.tight_layout()

# 添加统一颜色条（可选）
fig.subplots_adjust(right=0.85)  # 预留颜色条位置
cbar_ax = fig.add_axes([0.87, 0.15, 0.02, 0.7])  # 颜色条位置 [左, 下, 宽, 高]
sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=values.min(), vmax=values.max()))
sm.set_array([])  # 必须设置一个空数组，否则颜色条可能不显示
fig.colorbar(sm, cax=cbar_ax, ticks=values, label='Permafrost Status\n0 = Non - Permafrost, 1 = Permafrost, 3 = Degraded Area')

# 保存图片（可选）
if output_fig_path:
    plt.savefig(output_fig_path, dpi=300, bbox_inches='tight')
plt.show()