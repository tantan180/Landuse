import os
import glob
from osgeo import gdal

# 设置文件夹路径
tif_folder = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\result"
vector_path = r"E:\temp\cjy_shp"  # 替换为你的矢量边界文件路径
output_folder = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\result1"  # 输出结果文件夹

# 获取所有TIF文件
tif_files = glob.glob(os.path.join(tif_folder, "*TTOP.tif"))

# 设置gdalwarp命令进行裁剪
for tif_file in tif_files:
    output_tif = os.path.join(output_folder, os.path.basename(tif_file))

    # 构建gdalwarp命令
    cmd = f"gdalwarp -cutline {vector_path} -crop_to_cutline -of GTiff {tif_file} {output_tif}"

    # 执行命令
    os.system(cmd)
    print(f"裁剪完成: {output_tif}")

#成功运行