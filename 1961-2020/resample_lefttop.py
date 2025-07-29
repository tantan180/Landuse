import os
import glob
import rasterio

# 路径设置
template_tif = r"E:\GEOdata\长江源\cjy_raster.tif"  # 选择一个标准栅格
input_folder = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\cjy1961_2020"
output_folder = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\TTOP_albers_1km_alignedd"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 读取模板信息
with rasterio.open(template_tif) as src:
    bounds = src.bounds
    res = src.res
    # 用 proj4 明确写死（推荐，别直接用src.crs）
    proj4 = "+proj=aea +lat_1=27 +lat_2=45 +lat_0=35 +lon_0=105 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    te = f"{bounds.left} {bounds.bottom} {bounds.right} {bounds.top}"
    tr = f"{res[0]} {res[1]}"

tif_files = glob.glob(os.path.join(input_folder, "*.tif"))
for tif_file in tif_files:
    output_tif = os.path.join(output_folder, os.path.basename(tif_file))
    cmd = (
        f'gdalwarp -te {te} -tr {tr} -t_srs "{proj4}" -tap -r bilinear "{tif_file}" "{output_tif}"'
    )
    os.system(cmd)
    print(f"已对齐: {output_tif}")