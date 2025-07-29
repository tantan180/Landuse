import os
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from glob import glob
from matplotlib.colors import ListedColormap


def calculate_total_degradation(t0_path, t11_path, output_path):
    """
    计算1961 - 2020年总退化区域（T0=1961年，T11=2020年）
    输出栅格：1=冻土，0=非冻土，3=总退化区，保留原始nodata值
    """
    with rasterio.open(t0_path) as t0_ds, rasterio.open(t11_path) as t11_ds:
        t0_data = t0_ds.read(1)
        t11_data = t11_ds.read(1)

        t0_nodata = t0_ds.nodata
        t11_nodata = t11_ds.nodata

        assert t0_data.shape == t11_data.shape, "两个栅格数据形状不一致"
        assert t0_ds.meta["transform"] == t11_ds.meta["transform"], "两个栅格地理变换不一致"
        assert t0_ds.meta["crs"] == t11_ds.meta["crs"], "两个栅格坐标系不一致"

        output = t11_data.copy().astype(np.float32)

        output = np.where((t0_data == 1) & (t11_data == 0), 3, output)

        if t0_nodata is not None:
            output = np.where(t0_data == t0_nodata, t0_nodata, output)
        if t11_nodata is not None:
            output = np.where(t11_data == t11_nodata, t11_nodata, output)

        meta = t0_ds.meta.copy()
        meta.update(
            dtype=rasterio.float32,
            nodata=t0_nodata
        )

        with rasterio.open(output_path, 'w', **meta) as output_ds:
            output_ds.write(output, 1)
    return output, t0_nodata  # 返回计算结果和nodata值，用于绘图


def plot_and_save_result(output_data, nodata, output_fig_path):
    """
    绘制总退化区域结果并保存为图片
    :param output_data: 总退化区域计算结果数组
    :param nodata: 无数据值
    :param output_fig_path: 图片输出路径
    """
    # 掩膜无数据值
    if nodata is not None:
        output_data = np.ma.masked_equal(output_data, nodata)

    # 自定义颜色映射：0-蓝色（非冻土）、1-白色（冻土）、3-红色（总退化区），nodata-灰色
    colors = ['#0000FF', '#FFFFFF', '#FF0000', '#808080']
    cmap = ListedColormap(colors)
    bounds = [0, 1, 3, np.finfo(np.float32).max]  # 颜色分段边界
    norm = plt.matplotlib.colors.BoundaryNorm(bounds, cmap.N)

    plt.figure(figsize=(10, 8))
    im = plt.imshow(output_data, cmap=cmap, norm=norm)

    # 添加颜色条
    cbar = plt.colorbar(im, ticks=[0.5, 1.5, 3.5], boundaries=bounds)
    cbar.ax.set_yticklabels(['Non - Permafrost', 'Permafrost', 'Degraded Area'])
    cbar.set_label('Permafrost Status')

    plt.title('Total Degradation Area (1961-2020)')
    plt.axis('off')  # 隐藏坐标轴
    plt.savefig(output_fig_path, dpi=300, bbox_inches='tight')
    plt.close()


def main():
    input_folder = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\result1"
    output_raster_path = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\total_degradation.tif"
    output_fig_path = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\picture\total_degradation.png"  # 图片输出路径

    raster_paths = sorted(glob(os.path.join(input_folder, "fused_*.tif")))
    if len(raster_paths) < 12:
        print("错误：至少需要12期栅格数据（1961-2020年）")
        return

    t0_path = raster_paths[0]
    t11_path = raster_paths[-1]

    output_data, nodata = calculate_total_degradation(t0_path, t11_path, output_raster_path)
    plot_and_save_result(output_data, nodata, output_fig_path)
    print(f"总退化区域栅格已保存至: {output_raster_path}")
    print(f"总退化区域可视化图片已保存至: {output_fig_path}")


if __name__ == "__main__":
    main()