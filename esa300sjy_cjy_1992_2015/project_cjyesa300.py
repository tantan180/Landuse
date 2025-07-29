import os
from osgeo import gdal, osr


def reproject_raster(input_path, output_path):
    """
    将栅格数据从WGS84投影到Albers等积圆锥投影（使用最邻近法）
    """
    # 定义目标投影参数（来自图片中的信息）
    albers_proj = """
    PROJCS["Albers_Conical_Equal_Area_cjy",
        GEOGCS["WGS 84",
            DATUM["WGS_1984",
                SPHEROID["WGS 84",6378137,298.257223563,
                    AUTHORITY["EPSG","7030"]],
                AUTHORITY["EPSG","6326"]],
            PRIMEM["Greenwich",0,
                AUTHORITY["EPSG","8901"]],
            UNIT["degree",0.0174532925199433,
                AUTHORITY["EPSG","9122"]],
            AUTHORITY["EPSG","4326"]],
        PROJECTION["Albers_Conic_Equal_Area"],
        PARAMETER["False_Easting",0.0],
        PARAMETER["False_Northing",0.0],
        PARAMETER["Central_Meridian",95.0],
        PARAMETER["Standard_Parallel_1",32.0],
        PARAMETER["Standard_Parallel_2",35.0],
        PARAMETER["Latitude_Of_Origin",30.0],
        UNIT["Meter",1.0]]
    """

    # 创建目标空间参考
    target_srs = osr.SpatialReference()
    target_srs.ImportFromWkt(albers_proj)

    # 打开输入文件
    input_ds = gdal.Open(input_path)

    # 创建输出文件 - 使用最邻近法重采样
    output_ds = gdal.Warp(output_path, input_ds,
                          dstSRS=target_srs,
                          format='GTiff',
                          resampleAlg=gdal.GRA_NearestNeighbour,  # 最邻近法
                          creationOptions=['COMPRESS=LZW'])

    # 关闭数据集
    input_ds = None
    output_ds = None


def batch_reproject(input_dir, output_dir):
    """
    批量处理1992-2015年的土地利用分类数据
    """
    # 确保输入目录存在
    if not os.path.exists(input_dir):
        print(f"错误：输入目录不存在 - {input_dir}")
        return

    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 处理每个TIFF文件
    for file_name in os.listdir(input_dir):
        if file_name.lower().endswith('.tif') and "cjy300_" in file_name:
            input_path = os.path.join(input_dir, file_name)

            # 保持原始文件名，只修改扩展名（可选）
            output_name = os.path.splitext(file_name)[0] + "_albers.tif"
            output_path = os.path.join(output_dir, output_name)

            print(f"正在处理: {input_path}")
            try:
                reproject_raster(input_path, output_path)
                print(f"已保存到: {output_path}")
            except Exception as e:
                print(f"处理文件 {input_path} 时出错: {str(e)}")


# 使用示例
if __name__ == "__main__":
    # 使用原始字符串避免转义问题
    input_directory = r"E:\GEOdata\LUCC\1992-2015ESA300\cjy1992_2015"
    output_directory = r"E:\GEOdata\LUCC\1992-2015ESA300\cjy1992_2015_albers"

    # 打印路径确认
    print(f"输入目录: {input_directory}")
    print(f"输出目录: {output_directory}")

    batch_reproject(input_directory, output_directory)
    print("所有文件处理完成！")