import os
import glob
from osgeo import gdal


def build_pyramids_for_cog_data(clipped_dir):
    """
    专门处理COG格式的TIFF文件建立金字塔
    """
    # 设置GDAL异常处理
    gdal.UseExceptions()

    # 强制设置COG忽略选项（适用于GDAL 3.4+）
    gdal.SetConfigOption('GDAL_IGNORE_COG_LAYOUT_BREAK', 'YES')
    gdal.SetConfigOption('GDAL_PAM_ENABLED', 'NO')  # 禁用元数据文件生成

    # 获取目录中所有TIFF文件
    tif_files = glob.glob(os.path.join(clipped_dir, "*.tif"))

    if not tif_files:
        print(f"警告: 目录 {clipped_dir} 中没有找到TIFF文件")
        return

    print(f"找到 {len(tif_files)} 个TIFF文件需要建立金字塔...")

    for tif_path in tif_files:
        filename = os.path.basename(tif_path)
        print(f"正在处理: {filename}")

        try:
            # 使用更底层的OpenEx方法，确保COG文件可写
            ds = gdal.OpenEx(tif_path,
                             gdal.OF_UPDATE | gdal.OF_VERBOSE_ERROR,
                             open_options=['IGNORE_COG_LAYOUT_BREAK=YES'])

            if ds is None:
                print(f"无法打开文件: {filename}")
                continue

            # 构建金字塔（使用DEFLATE压缩）
            print("正在构建金字塔...")
            ds.BuildOverviews(
                "NEAREST",
                [2, 4, 8, 16, 32, 64],  # 更完整的金字塔层级
                options=["COMPRESS_OVERVIEW=DEFLATE",
                         "TILED_OVERVIEW=YES",
                         "NUM_THREADS=ALL_CPUS"]  # 多线程加速
            )

            # 显式关闭数据集
            ds = None
            print(f"成功为 {filename} 建立金字塔\n")

        except Exception as e:
            print(f"处理 {filename} 时出错: {str(e)}\n")


if __name__ == "__main__":
    # 设置路径
    clipped_data_dir = r"E:\GEOdata\LUCC\ESRI10\data\2017"

    # 打印GDAL版本信息
    print(f"使用的GDAL版本: {gdal.__version__}")
    print(f"正在处理目录: {clipped_data_dir}\n")

    # 调用函数
    build_pyramids_for_cog_data(clipped_data_dir)