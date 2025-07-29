import os
import rasterio
import numpy as np
from glob import glob


def calculate_degradation(t1_path, t2_path, output_path):
    """
    计算两个相邻时段的冻土退化区域
    :param t1_path: 前期冻土数据路径（T1）
    :param t2_path: 后期冻土数据路径（T2）
    :param output_path: 退化区域结果输出路径
    """
    with rasterio.open(t1_path) as t1_ds, rasterio.open(t2_path) as t2_ds:
        # 读取栅格数据
        t1_data = t1_ds.read(1)
        t2_data = t2_ds.read(1)

        # 确保两个栅格的形状和地理信息一致
        assert t1_data.shape == t2_data.shape, "两个栅格数据形状不一致"
        assert t1_ds.meta["transform"] == t2_ds.meta["transform"], "两个栅格地理变换不一致"
        assert t1_ds.meta["crs"] == t2_ds.meta["crs"], "两个栅格坐标系不一致"

        # 获取原始栅格的nodata值
        t1_nodata = t1_ds.nodata
        t2_nodata = t2_ds.nodata

        # 计算退化区域：前期是冻土（T1 == 1）且后期变为非冻土（T2 == 0），编码为 3
        degradation = np.where((t1_data == 1) & (t2_data == 0), 3, t1_data)

        # 处理nodata值（如果两个输入栅格中任意一个是nodata，则输出也设为nodata）
        if t1_nodata is not None:
            degradation = np.where(t1_data == t1_nodata, t1_nodata, degradation)
        if t2_nodata is not None:
            degradation = np.where(t2_data == t2_nodata, t2_nodata, degradation)

        # 更新元数据
        meta = t1_ds.meta.copy()

        # 检查原始nodata值是否适用于int32类型
        if (t1_nodata is not None and not isinstance(t1_nodata, int)) or \
                (t2_nodata is not None and not isinstance(t2_nodata, int)):
            # 如果原始nodata不是整数，设置新的int32范围内的nodata值
            new_nodata = -9999  # 选择一个不会出现在正常数据中的整数值
            degradation = np.where(degradation == t1_nodata, new_nodata, degradation)
            degradation = np.where(degradation == t2_nodata, new_nodata, degradation)
            meta.update(nodata=new_nodata)
        else:
            # 否则保持原始nodata值
            meta.update(nodata=t1_nodata)

        # 设置数据类型为int32
        meta.update(dtype=rasterio.int32)

        # 保存结果栅格
        with rasterio.open(output_path, 'w', **meta) as output_ds:
            output_ds.write(degradation, 1)


def batch_process_degradation(input_folder, output_folder):
    """
    批量处理逐时段冻土退化区域计算
    :param input_folder: 输入栅格数据所在文件夹，包含 12 期冻土数据
    :param output_folder: 输出退化区域结果的文件夹
    """
    # 获取输入文件夹中的栅格数据路径，按文件名排序
    raster_paths = sorted(glob(os.path.join(input_folder, "fused_*.tif")))

    # 检查是否至少有两期数据
    if len(raster_paths) < 2:
        print("输入文件夹中至少需要两期栅格数据")
        return

    # 创建输出文件夹
    os.makedirs(output_folder, exist_ok=True)

    # 逐时段处理
    for i in range(len(raster_paths) - 1):
        t1_path = raster_paths[i]
        t2_path = raster_paths[i + 1]

        # 提取时段信息，用于输出文件名
        t1_name = os.path.basename(t1_path).replace("fused_", "").replace("_TTOP.tif", "")
        t2_name = os.path.basename(t2_path).replace("fused_", "").replace("_TTOP.tif", "")
        output_file_name = f"degradation_{t1_name}_{t2_name}.tif"
        output_path = os.path.join(output_folder, output_file_name)

        calculate_degradation(t1_path, t2_path, output_path)
        print(f"已处理 {t1_name} - {t2_name} 时段，结果保存至 {output_path}")


if __name__ == "__main__":
    # 输入文件夹，包含 12 期冻土数据
    input_folder = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\result1"
    # 输出文件夹，用于保存退化区域结果
    output_folder = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\degradation_results"

    batch_process_degradation(input_folder, output_folder)