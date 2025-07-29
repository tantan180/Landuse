import rasterio
from rasterio.features import rasterize
import fiona
import numpy as np

# 输入路径
frozen_raster_path = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\TTOP_albers_1km_alignedd\1961_1965_TTOP.tif"  # 冻土栅格路径（获取空间参考和分辨率）
vector_shapefile_path = r"E:\temp\cjy_shp\cjy_region_Buffer.shp"  # 矢量边界路径（shp文件）

# 输出路径
output_tif_path = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\zero_template.tif"  # 输出全为0的栅格路径

# 1. 获取冻土栅格的空间参数（包括分辨率、空间参考）
with rasterio.open(frozen_raster_path) as src:
    meta = src.meta.copy()
    out_shape = src.shape
    transform = src.transform
    crs = src.crs

# 2. 读取矢量边界（shapefile）
with fiona.open(vector_shapefile_path, "r") as shapefile:
    shapes = [feature["geometry"] for feature in shapefile]

# 3. 栅格化，将矢量区域转为栅格，并设置值为0
zero_array = np.zeros(out_shape, dtype="uint8")

# 将矢量边界栅格化，填充为0
rasterized = rasterize(
    [(shape, 0) for shape in shapes],  # 给定shape及值
    out_shape=out_shape,
    transform=transform,
    fill=0,  # 默认填充值为0
    dtype="uint8"
)

# 4. 更新元数据
meta.update({"dtype": "uint8", "nodata": 0})

# 5. 保存为新栅格文件
with rasterio.open(output_tif_path, "w", **meta) as dst:
    dst.write(rasterized, 1)

print(f"栅格已生成并保存到: {output_tif_path}")
