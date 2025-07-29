import os
import glob
from osgeo import gdal


def build_pyramids_for_clipped_data(clipped_dir):
    """
    为Clipped_Data目录中的所有TIFF文件建立金字塔

    参数:
        clipped_dir: 包含裁剪后TIFF文件的目录路径
    """
    # 设置GDAL异常处理
    gdal.UseExceptions()

    # 获取目录中所有裁剪后的TIFF文件
    tif_files = glob.glob(os.path.join(clipped_dir, "*.tif"))

    if not tif_files:
        print(f"警告: 目录 {clipped_dir} 中没有找到符合模式的TIFF文件")
        return

    print(f"找到 {len(tif_files)} 个TIFF文件需要建立金字塔...")

    for tif_path in tif_files:
        filename = os.path.basename(tif_path)
        print(f"正在处理: {filename}")

        try:
            # 打开文件
            ds = gdal.Open(tif_path, gdal.GA_Update)

            # 建立金字塔（适用于分类数据，使用NEAREST重采样）
            ds.BuildOverviews(
                "NEAREST",
                [2, 4, 8, 16],  # 金字塔层级
                options=["COMPRESS_OVERVIEW=DEFLATE", "TILED_OVERVIEW=YES"]
            )

            # 关闭文件
            ds = None

            print(f"成功为 {filename} 建立金字塔")
        except Exception as e:
            print(f"处理 {filename} 时出错: {str(e)}")


if __name__ == "__main__":
    # 设置路径 -
    clipped_data_dir = r"E:\GEOdata\LUCC\1992-2015ESA300\cjy1992_2015_albers"

    # 调用函数建立金字塔
    build_pyramids_for_clipped_data(clipped_data_dir)
    #成功运行