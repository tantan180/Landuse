import os
import glob
import rasterio
from rasterio.mask import mask
import fiona


def batch_clip_raster(input_dir, output_dir, clip_shapefile):
    """
    批量裁剪栅格数据

    参数:
        input_dir: 输入文件夹路径（包含各年份子文件夹）
        output_dir: 输出文件夹路径
        clip_shapefile: 用于裁剪的矢量文件路径
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 读取裁剪范围
    with fiona.open(clip_shapefile, "r") as shapefile:
        shapes = [feature["geometry"] for feature in shapefile]

    # 遍历所有年份文件夹
    for year_dir in glob.glob(os.path.join(input_dir, "*")):
        if os.path.isdir(year_dir):
            year = os.path.basename(year_dir)
            print(f"正在处理 {year} 年数据...")

            # 创建年份输出目录
            year_output_dir = os.path.join(output_dir, year)
            os.makedirs(year_output_dir, exist_ok=True)

            # 处理该年份下的所有TIF文件
            for tif_file in glob.glob(os.path.join(year_dir, "*.tif")):
                filename = os.path.basename(tif_file)
                output_file = os.path.join(year_output_dir, filename)

                # 执行裁剪操作
                with rasterio.open(tif_file) as src:
                    out_image, out_transform = mask(src, shapes, crop=True)
                    out_meta = src.meta.copy()

                    # 更新元数据
                    out_meta.update({
                        "driver": "GTiff",
                        "height": out_image.shape[1],
                        "width": out_image.shape[2],
                        "transform": out_transform
                    })

                    # 写入输出文件
                    with rasterio.open(output_file, "w", **out_meta) as dest:
                        dest.write(out_image)

                print(f"已裁剪并保存: {output_file}")


if __name__ == "__main__":
    # 设置路径
    input_directory = r"E:\\GEOdata\\LUCC\\1980-2023_1kmCNLUCC\\250506_中科院全国1km土地利用历史数据\\中科院1km土地利用\\TIF格式"  # 替换为您的CNLUCC数据根目录
    output_directory = r"E:\\GEOdata\\LUCC\\1980-2023_1kmCNLUCC\\CNLUCC_clipped"  # 替换为您想要的输出目录
    clip_shapefile_path = r"E:\\GEOdata\\LUCC\\1980-2023_1kmCNLUCC\\cjy_region_CNLUCC.shp"  # 替换为您的研究区边界文件

    # 执行批量裁剪
    batch_clip_raster(input_directory, output_directory, clip_shapefile_path)
    print("所有年份数据裁剪完成！")
    #成功处理