import os
from osgeo import gdal


def find_tif_files(root_folder):
    """递归查找所有TIF文件"""
    tif_files = []
    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.lower().endswith('.tif'):
                tif_files.append(os.path.join(root, file))
    return tif_files


def merge_tifs(tif_files, output_file):
    """合并多个TIF文件"""
    # 显式启用GDAL异常
    gdal.UseExceptions()

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    if not tif_files:
        raise ValueError("没有找到任何TIFF文件")

    print(f"找到 {len(tif_files)} 个TIFF文件，开始合并...")

    # 使用gdal.Warp直接合并
    warp_options = gdal.WarpOptions(
        format='GTiff',
        creationOptions=['COMPRESS=LZW', 'BIGTIFF=IF_SAFER'],
        resampleAlg='near'  # 使用最近邻法，适合分类数据
    )

    gdal.Warp(output_file, tif_files, options=warp_options)
    print(f"合并完成，结果保存在: {output_file}")


# 使用示例
if __name__ == "__main__":
    # 设置包含多个子文件夹的根目录
    root_folder = r"E:\GEOdata\LUCC\中国土地利用GlobeLand30_2000_2010_2020\GlobeLand30_2020\GlobeLand30_2020\GlobeLand30"
    output_file = r"E:\GEOdata\LUCC\中国土地利用GlobeLand30_2000_2010_2020\GlobeLand30_2020\merged.tif"

    # 查找所有TIF文件
    tif_files = find_tif_files(root_folder)

    # 合并文件
    merge_tifs(tif_files, output_file)
