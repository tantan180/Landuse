import os
import glob
import warnings
from osgeo import gdal, ogr


def batch_clip_tif(input_dir, output_dir, shp_path, years=None):
    """
    批量裁剪TIFF文件

    参数:
        input_dir: 输入目录路径(包含年份子文件夹的目录)
        output_dir: 输出目录路径
        shp_path: 用于裁剪的矢量文件路径
        years: 可选，指定要处理的年份列表，如[1985, 1990, 1995]
    """
    # 设置GDAL异常处理
    gdal.UseExceptions()

    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 如果没有指定年份，则处理所有年份
    if years is None:
        # 获取所有年份文件夹
        year_folders = glob.glob(os.path.join(input_dir, '*_TTOP'))
        years = [os.path.basename(f).split('_')[0] for f in year_folders]

    # 处理每个年份
    for year in years:
        # 构建输入文件夹路径
        year_folder = os.path.join(input_dir, f"{year}_TTOP")

        # 查找该年份下的TIFF文件
        tif_files = glob.glob(os.path.join(year_folder, '*.tif'))

        if not tif_files:
            print(f"警告: {year}年文件夹中没有找到TIFF文件")
            continue

        # 假设每个年份文件夹只有一个主要的TIFF文件
        input_tif = tif_files[0]

        # 构建输出文件名
        output_tif = os.path.join(output_dir, f"GLC_FCS30_{year}_clip.tif")

        print(f"正在处理: {year}年数据...")

        try:
            # 使用gdal.Warp进行裁剪
            gdal.Warp(
                output_tif,
                input_tif,
                cutlineDSName=shp_path,
                cropToCutline=True,
                dstNodata=0  # 设置nodata值
            )
            print(f"成功裁剪并保存: {output_tif}")
        except Exception as e:
            print(f"处理{year}年数据时出错: {str(e)}")


if __name__ == "__main__":
    # 设置路径 (根据您的实际路径修改)
    base_dir = r"E:\GEOdata\冻土分布\青藏高原冻土变化数据集（1961-2020）\下载\青藏高原冻土变化数据集（1961-2020）\Frozen ground change data set in the Tibetan Plateau\TTOP"
    output_dir = r"E:\GEOdata\冻土分布\青藏高原冻土变化数据集（1961-2020）\cjy1961_2020"  # 输出目录
    shp_file = r"E:\GEOdata\长江源\长江源区径流及土壤水分变化（2003-2018）\cjy_region_Buffer.shp"  # 替换为您的矢量文件路径

    # 可选: 指定要处理的特定年份
    #selected_years = [1990, 1995, 2000, 2005, 2010, 2021, 2022]

    # 调用函数处理所有年份
    batch_clip_tif(base_dir, output_dir, shp_file)
    # 如果只想处理特定年份: batch_clip_tif(base_dir, output_dir, shp_file, selected_years)
    #成功运行