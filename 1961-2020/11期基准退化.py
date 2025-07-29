import os
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from glob import glob
from matplotlib.colors import ListedColormap

# --------------------------
# 1. 配置参数
# --------------------------
# 输入文件夹（包含12期数据，第一期为1961-1965基准数据）
input_folder = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\result1"
# 输出图片路径
output_fig_path = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\picture\degradation_evolution.png"

# 颜色映射：0=非冻土（蓝），1=冻土（白），2=退化区（红），nodata=灰色（不显示）
cmap = ListedColormap(['#1f77b4', '#ffffff', '#ff0000'])  # 0:蓝, 1:白, 2:红
labels = ['Non-Permafrost', 'Permafrost', 'Degraded Area']  # 颜色条标签

# --------------------------
# 2. 读取数据并处理退化区
# --------------------------
# 读取所有12期数据（按时间排序）
raster_paths = sorted(glob(os.path.join(input_folder, "fused_*.tif")))
if len(raster_paths) != 12:
    raise ValueError("输入文件夹必须包含12期数据（第一期为1961-1965）")

# 读取基准数据（1961-1965）
with rasterio.open(raster_paths[0]) as base_ds:
    base_data = base_ds.read(1)  # 基准数据：1=冻土，0=非冻土
    base_nodata = base_ds.nodata  # 基准数据的nodata值
    meta = base_ds.meta  # 保留地理信息用于验证

# 存储处理后的12期数据（第一期为基准数据，后续为对比结果）
processed_data = [base_data]  # 第1期：原始基准数据
time_labels = [os.path.basename(raster_paths[0]).replace("fused_", "").replace("_TTOP.tif", "")]  # 基准期标签

# 处理后续11期数据（与基准对比）
for i in range(1, 12):
    with rasterio.open(raster_paths[i]) as curr_ds:
        # 验证地理信息一致性
        assert curr_ds.meta["transform"] == meta["transform"], f"第{i + 1}期与基准数据地理变换不一致"
        assert curr_ds.meta["crs"] == meta["crs"], f"第{i + 1}期与基准数据坐标系不一致"

        curr_data = curr_ds.read(1)  # 当前期数据：1=冻土，0=非冻土
        curr_nodata = curr_ds.nodata  # 当前期nodata值

        # 初始化结果数组（默认使用当前期数据）
        result = curr_data.copy().astype(np.float32)# 用float32兼容nodata的浮点值

        # 标记退化区：基准=1（冻土）且当前期=0（非冻土）→ 2（退化）
        result = np.where(
            (base_data == 1) & (curr_data == 0),  # 退化条件
            2,  # 满足条件→退化区（2）
            result  # 不满足条件→保留当前期值（0或1）
        )

        # 处理nodata：基准或当前期为nodata→结果为nodata
        if base_nodata is not None:
            result = np.where(base_data == base_nodata, base_nodata, result)
        if curr_nodata is not None:
            result = np.where(curr_data == curr_nodata, curr_nodata, result)

        processed_data.append(result)
        # 提取当前期标签（如1966-1970）
        time_labels.append(os.path.basename(raster_paths[i]).replace("fused_", "").replace("_TTOP.tif", ""))

# --------------------------
# 3. 绘制时间序列图
# --------------------------
rows = 3  # 3行
cols = 4  # 4列（共12个子图）
fig, axes = plt.subplots(rows, cols, figsize=(16, 12))
axes = axes.flatten()  # 转为一维数组方便遍历

for i, (data, ax, label) in enumerate(zip(processed_data, axes, time_labels)):
    # 掩膜nodata值（不显示）

    masked_data = data
    if base_nodata is not None:
        masked_data = np.ma.masked_equal(masked_data, base_nodata)
    if curr_nodata is not None:
        masked_data = np.ma.masked_equal(masked_data, curr_nodata)  # 优化点2

    # 绘制栅格
    im = ax.imshow(masked_data, cmap=cmap, vmin=0, vmax=2, clim=(0, 2))  # # 锁定颜色映射范围
    ax.set_title(label, fontsize=8)  # 子图标题（时段）
    ax.axis('off')  # 隐藏坐标轴

# 调整布局
plt.tight_layout(rect=[0, 0, 0.9, 1])  # 预留右侧颜色条位置

# 添加统一颜色条
cbar_ax = fig.add_axes([0.92, 0.15, 0.02, 0.7])  # 颜色条位置 [左, 下, 宽, 高]
cbar = fig.colorbar(im, cax=cbar_ax, ticks=[0, 1, 2])
cbar.ax.set_yticklabels(labels, fontsize=10)
cbar.set_label('Permafrost Status', fontsize=12)

# 保存图片
plt.savefig(output_fig_path, dpi=300, bbox_inches='tight')
print(f"退化区演变时间序列图已保存至: {output_fig_path}")

plt.show()