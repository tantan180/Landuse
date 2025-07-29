import os
import rasterio
import numpy as np
from glob import glob


def calculate_total_degradation(t0_path, t11_path, output_path):
    """
    计算1961-2020年总退化区域（T0=1961年，T11=2020年）
    输出栅格：1=冻土，0=非冻土，3=总退化区，保留原始nodata值
    """
    with rasterio.open(t0_path) as t0_ds, rasterio.open(t11_path) as t11_ds:
        # 读取栅格数据
        t0_data = t0_ds.read(1)
        t11_data = t11_ds.read(1)

        # 获取原始nodata值
        t0_nodata = t0_ds.nodata
        t11_nodata = t11_ds.nodata

        # 确保两个栅格的形状和地理信息一致
        assert t0_data.shape == t11_data.shape, "两个栅格数据形状不一致"
        assert t0_ds.meta["transform"] == t11_ds.meta["transform"], "两个栅格地理变换不一致"
        assert t0_ds.meta["crs"] == t11_ds.meta["crs"], "两个栅格坐标系不一致"

        # 初始化输出数组，默认为T11的状态（0=非冻土，1=冻土）
        # 先转换为float32，避免int32无法存储nodata的问题
        output = t11_data.copy().astype(np.float32)

        # 标记总退化区：T0=1且T11=0的区域标记为3
        output = np.where((t0_data == 1) & (t11_data == 0), 3, output)

        # 恢复原始nodata值（如果T0或T11是nodata，则输出也为nodata）
        if t0_nodata is not None:
            output = np.where(t0_data == t0_nodata, t0_nodata, output)
        if t11_nodata is not None:
            output = np.where(t11_data == t11_nodata, t11_nodata, output)

        # 更新元数据：使用float32存储nodata值
        meta = t0_ds.meta.copy()
        meta.update(
            dtype=rasterio.float32,  # 改用float32存储数据
            nodata=t0_nodata  # 保持原始nodata值
        )

        # 保存结果栅格
        with rasterio.open(output_path, 'w', **meta) as output_ds:
            output_ds.write(output, 1)


def main():
    # 输入文件夹：包含所有12期冻土数据（1961-2020年）
    input_folder = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\result1"
    # 输出路径：总退化区域结果
    output_path = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\total_degradation.tif"

    # 获取所有栅格路径并按时间排序
    raster_paths = sorted(glob(os.path.join(input_folder, "fused_*.tif")))
    if len(raster_paths) < 12:
        print("错误：至少需要12期栅格数据（1961-2020年）")
        return

    # 最早一期（1961年）和最后一期（2020年）的路径
    t0_path = raster_paths[0]  # 假设第1个文件是1961年
    t11_path = raster_paths[-1]  # 假设最后1个文件是2020年

    # 计算总退化区域
    calculate_total_degradation(t0_path, t11_path, output_path)
    print(f"总退化区域已保存至: {output_path}")


if __name__ == "__main__":
    main()